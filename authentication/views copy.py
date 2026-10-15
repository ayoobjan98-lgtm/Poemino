import logging
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import View

from authentication.models import (
    FaceReference,
    VerificationSession,
    OTPToken,
)
from authentication.services.face_detection import detect_faces
from authentication.services.face_verification import (
    extract_face_feature,
    compare_features,
    check_duplicate_face,
    embed_from_json,
    embed_to_json,
)
from authentication.services.video_processing import extract_frames, delete_temp_dir
from authentication.services.liveness import detect_liveness
from authentication.services.otp import create_otp_for_user, send_otp_email, verify_otp
from authentication.services.dashboard_access import (
    has_valid_dashboard_access,
    grant_dashboard_access,
)

logger = logging.getLogger(__name__)


class DuplicateFaceError(Exception):
    """Face is already registered to another user."""


def has_completed_verification_session(user):
    return VerificationSession.objects.filter(
        user=user,
        status='completed',
        expires_at__gt=timezone.now(),
    ).exists()


class VideoVerificationView(LoginRequiredMixin, View):
    template_name = 'authentication/verify.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return redirect('login')

        if not getattr(user, 'is_page_permitted', False):
            return render(request, '404.html', status=404)

        if has_valid_dashboard_access(user):
            return redirect('dashboard:index')

        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        user = request.user
        try:
            ref = self._get_face_reference(user)
        except DuplicateFaceError:
            return render(request, '404.html', status=404)

        if ref is None:
            return render(request, 'authentication/error.html')
        return render(request, self.template_name)

    def post(self, request):
        user = request.user

        # Cache the reference so we don't hit the DB again later.
        try:
            ref = self._get_face_reference(user)
        except DuplicateFaceError:
            return render(request, '404.html', status=404)

        if ref is None:
            return render(request, 'authentication/error.html')

        # Single query to detect a pending verification.
        if VerificationSession.objects.filter(user=user, status='pending').exists():
            messages.error(request, _('Verification already in progress.'))
            return render(request, self.template_name)

        video_file = request.FILES.get('video')
        if not video_file:
            messages.error(request, _('Please record and upload a video.'))
            return render(request, self.template_name)

        if video_file.size > 20 * 1024 * 1024:
            messages.error(request, _('Video too large (max 20 MB).'))
            return render(request, self.template_name)

        if not video_file.content_type.startswith('video/'):
            messages.error(request, _('Invalid file type. Expected a video.'))
            return render(request, self.template_name)

        session = VerificationSession.objects.create(user=user, video=video_file)

        try:
            frames, temp_dir = extract_frames(session.video.path, num_frames=5)
            if len(frames) < 2:
                raise ValueError(_("Not enough frames could be extracted from the video."))

            # ref is already loaded — no extra query.
            ref_embedding = embed_from_json(ref.embedding)

            duplicate_detected = False
            match_count = 0

            for frame_path in frames:
                try:
                    img = cv2.imread(frame_path)
                    faces = detect_faces(img)
                    if len(faces) != 1:
                        continue
                    feature = extract_face_feature(img, faces[0]['bbox'])

                    if check_duplicate_face(user, feature):
                        duplicate_detected = True
                        break

                    similarity = compare_features(ref_embedding, feature)
                    if similarity >= getattr(settings, 'FACE_MATCH_THRESHOLD', 0.6):
                        match_count += 1
                except Exception:
                    continue

            if duplicate_detected:
                raise DuplicateFaceError()

            if match_count < len(frames) * 0.6:
                raise ValueError(_("Face does not match the registered identity."))

            is_live, _ = detect_liveness(frames)
            if not is_live:
                raise ValueError(_("Liveness check failed. Please record a fresh video."))

            session.status = 'completed'
            session.save(update_fields=['status'])
            delete_temp_dir(temp_dir)

            otp = create_otp_for_user(user)
            send_otp_email(user, otp)

            messages.success(request, _('Verification passed. OTP sent to your email.'))
            return redirect('authentication:otp')

        except DuplicateFaceError:
            session.status = 'failed'
            session.save(update_fields=['status'])
            if 'temp_dir' in locals():
                delete_temp_dir(temp_dir)
            return render(request, '404.html', status=404)

        except Exception as e:
            session.status = 'failed'
            session.save(update_fields=['status'])
            if 'temp_dir' in locals():
                delete_temp_dir(temp_dir)
            messages.error(request, str(e))
            return render(request, self.template_name)

    def _get_face_reference(self, user):
        """
        Return the user's FaceReference, creating it from the approved
        dashboard registration photo if needed.

        Returns the FaceReference instance, or None if it cannot be obtained.
        Raises DuplicateFaceError if the face matches another user.
        """
        # Fast path: reference already exists (1 query).
        ref = FaceReference.objects.filter(user=user).first()
        if ref:
            return ref

        try:
            from dashboard.models import ContentManagerRegistration

            # Match by username OR by the email on the related request.
            registration = ContentManagerRegistration.objects.filter(
                Q(username=user.username) | Q(request__email=user.email),
                status='approved',
            ).first()
            if not registration or not registration.photo:
                return None

            registration.photo.seek(0)
            file_bytes = registration.photo.read()

            img = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                try:
                    pil_img = Image.open(BytesIO(file_bytes))
                    pil_img = pil_img.convert('RGB')
                    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                except Exception:
                    return None

            if img is None:
                return None

            faces = detect_faces(img)
            if len(faces) != 1:
                return None

            feature = extract_face_feature(img, faces[0]['bbox'])

            if check_duplicate_face(user, feature):
                raise DuplicateFaceError()

            safe_name = f'face_reference_{user.pk}.jpg'
            ref = FaceReference.objects.create(
                user=user,
                image=ContentFile(file_bytes, name=safe_name),
                embedding=embed_to_json(feature),
            )
            return ref

        except DuplicateFaceError:
            raise
        except Exception:
            logger.exception("Failed to create FaceReference for user %s", user.username)
            return None



class OTPVerificationView(LoginRequiredMixin, View):
    template_name = 'authentication/otp.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return redirect('login')

        if not getattr(user, 'is_page_permitted', False):
            return render(request, '404.html', status=404)

        if has_valid_dashboard_access(user):
            return redirect('dashboard:index')

        if not has_completed_verification_session(user):
            return render(request, '404.html', status=404)

        # Single query for a valid unused OTP.
        if not OTPToken.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).exists():
            return render(request, '404.html', status=404)

        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        otp = request.POST.get('otp', '').strip()
        success, msg = verify_otp(request.user, otp)

        if success:
            grant_dashboard_access(request.user, request)
            VerificationSession.objects.filter(
                user=request.user,
                status='completed',
            ).delete()
            messages.success(
                request,
                _('Identity verified. Dashboard access granted for 7 days.'),
            )
            return redirect('dashboard:index')

        messages.error(request, msg)
        return render(request, self.template_name)