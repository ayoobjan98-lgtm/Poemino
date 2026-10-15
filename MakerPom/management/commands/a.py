import re
import time
import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from google.cloud import translate_v3 as translate
from google.api_core import exceptions as google_exceptions
from google.auth import default as google_auth_default
import polib

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Translate user-facing strings from Django templates using Google Cloud Translation API.'

    def add_arguments(self, parser):
        parser.add_argument('--source', required=True, help='Source language code (e.g., fa)')
        parser.add_argument('--target', required=True, help='Target language code (e.g., en)')
        parser.add_argument('--compile', action='store_true',
                            help='Compile .po to .mo after translation')
        parser.add_argument('--dry-run', action='store_true',
                            help='Scan and report without calling API or writing files')
        parser.add_argument('--batch-size', type=int, default=100,
                            help='Number of strings per API request (default 100)')
        parser.add_argument('--template-dir', type=str,
                            help='Custom template directory (default: first entry in settings.TEMPLATES[0]["DIRS"] or BASE_DIR/templates)')
        parser.add_argument('--locale-dir', type=str,
                            help='Custom locale directory (default: settings.LOCALE_PATHS[0] or BASE_DIR/locale)')

    def handle(self, *args, **options):
        source_lang = options['source']
        target_lang = options['target']
        do_compile = options['compile']
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        # 1. Determine directories
        template_dir = self._get_template_dir(options['template_dir'])
        locale_dir = self._get_locale_dir(options['locale_dir'])

        self.stdout.write(f'Scanning templates in: {template_dir}')
        self.stdout.write(f'Locale directory: {locale_dir}')

        if not template_dir.exists():
            raise CommandError(f'Template directory does not exist: {template_dir}')

        # 2. Extract translatable strings
        extracted_strings = extract_translatable_strings(template_dir)
        total_detected = len(extracted_strings)
        self.stdout.write(f'Detected {total_detected} unique user-facing strings.')

        # 3. Load existing .po file for target language
        po_path = locale_dir / target_lang / 'LC_MESSAGES' / 'django.po'
        po = self._load_or_create_po(po_path)

        # Build set of already translated msgids
        already_translated = set()
        for entry in po:
            if entry.msgstr and not entry.fuzzy:
                already_translated.add(entry.msgid)

        strings_to_translate = [s for s in extracted_strings if s not in already_translated]
        self.stdout.write(f'Already translated (skipped): {len(already_translated)}')
        self.stdout.write(f'Strings to translate: {len(strings_to_translate)}')

        # 4. Dry-run: report and exit
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN: No API calls, no file modifications.'))
            self._print_strings(strings_to_translate)
            self._print_summary(
                total_detected=total_detected,
                already_translated=len(already_translated),
                sent=len(strings_to_translate),
                succeeded=0,
                failed=0,
                po_path=po_path,
                mo_path=None,
                status='dry-run'
            )
            return

        # 5. If nothing to translate, optionally compile and exit
        if not strings_to_translate:
            self.stdout.write(self.style.SUCCESS('No new strings to translate.'))
            if do_compile:
                self._compile_and_verify(locale_dir, target_lang)
            self._print_summary(
                total_detected=total_detected,
                already_translated=len(already_translated),
                sent=0,
                succeeded=0,
                failed=0,
                po_path=po_path,
                mo_path=locale_dir / target_lang / 'LC_MESSAGES' / 'django.mo' if do_compile else None,
                status='success'
            )
            return

        # 6. Resolve Google Cloud project ID via ADC or settings
        #    (No hard requirement at startup; only needed for actual translation)
        try:
            credentials, project_id = google_auth_default()
        except Exception as e:
            raise CommandError(f'Failed to obtain Google credentials: {e}')

        # Fallback to settings if ADC did not provide a project ID
        if not project_id:
            project_id = getattr(settings, 'GOOGLE_PROJECT_ID', None)

        if not project_id:
            raise CommandError(
                'No Google Cloud project ID could be resolved. '
                'Set GOOGLE_CLOUD_PROJECT environment variable, '
                'or ensure your Application Default Credentials include a project ID.'
            )

        # 7. Initialize Google Translate client with resolved credentials
        try:
            client = translate.TranslationServiceClient(credentials=credentials)
        except Exception as e:
            raise CommandError(f'Failed to initialize Google Translate client: {e}')

        # 8. Translate in batches with retry
        translations = {}
        total_succeeded = 0
        total_failed = 0
        batches = self._chunk_list(strings_to_translate, batch_size)

        for i, batch in enumerate(batches, 1):
            self.stdout.write(f'Translating batch {i}/{len(batches)} ({len(batch)} strings)...')
            # Protect placeholders
            protected_batch = []
            mappings = []
            for text in batch:
                protected, mapping = protect_placeholders(text)
                protected_batch.append(protected)
                mappings.append(mapping)

            try:
                translated_texts = translate_with_retry(
                    client, project_id, protected_batch, source_lang, target_lang
                )
                # Unprotect placeholders
                for original, translated, mapping in zip(batch, translated_texts, mappings):
                    translations[original] = unprotect_placeholders(translated, mapping)
                total_succeeded += len(batch)
            except Exception as e:
                total_failed += len(batch)
                self.stderr.write(self.style.ERROR(
                    f'Permanent failure translating batch {i}: {e}'
                ))
                # Abort without writing anything
                self._print_summary(
                    total_detected=total_detected,
                    already_translated=len(already_translated),
                    sent=len(strings_to_translate),
                    succeeded=total_succeeded,
                    failed=total_failed,
                    po_path=po_path,
                    mo_path=None,
                    status='failure'
                )
                raise CommandError('Translation failed. Existing catalogs left untouched.')

        # 9. Update .po file (all translations succeeded by this point)
        self.stdout.write('All translations succeeded. Updating .po file...')
        for original, translated in translations.items():
            entry = po.find(original)
            if entry:
                entry.msgstr = translated
                if 'fuzzy' in entry.flags:
                    entry.flags.remove('fuzzy')
            else:
                po.append(polib.POEntry(msgid=original, msgstr=translated))

        # Ensure directory exists and save
        po_path.parent.mkdir(parents=True, exist_ok=True)
        po.save(str(po_path))
        self.stdout.write(self.style.SUCCESS(f'Updated {po_path}'))

        # 10. Compile if requested
        mo_path = None
        if do_compile:
            self._compile_and_verify(locale_dir, target_lang)
            mo_path = locale_dir / target_lang / 'LC_MESSAGES' / 'django.mo'

        # 11. Final summary
        self._print_summary(
            total_detected=total_detected,
            already_translated=len(already_translated),
            sent=len(strings_to_translate),
            succeeded=total_succeeded,
            failed=total_failed,
            po_path=po_path,
            mo_path=mo_path,
            status='success' if total_failed == 0 else 'failure'
        )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _get_template_dir(self, custom_dir):
        if custom_dir:
            return Path(custom_dir).resolve()
        # Use first template dir from settings
        try:
            dirs = settings.TEMPLATES[0]['DIRS']
            if dirs:
                return Path(dirs[0]).resolve()
        except (IndexError, KeyError):
            pass
        return settings.BASE_DIR / 'templates'

    def _get_locale_dir(self, custom_dir):
        if custom_dir:
            return Path(custom_dir).resolve()
        if settings.LOCALE_PATHS:
            return Path(settings.LOCALE_PATHS[0]).resolve()
        return settings.BASE_DIR / 'locale'

    def _load_or_create_po(self, po_path):
        if po_path.exists():
            try:
                po = polib.pofile(str(po_path))
                self.stdout.write(f'Loaded existing .po: {po_path}')
                return po
            except Exception as e:
                self.stderr.write(f'Warning: could not parse {po_path}: {e}. Creating new.')
        # Create new PO file with metadata
        po = polib.POFile()
        po.metadata = {
            'Project-Id-Version': 'PACKAGE VERSION',
            'Report-Msgid-Bugs-To': '',
            'POT-Creation-Date': time.strftime('%Y-%m-%d %H:%M%z'),
            'PO-Revision-Date': time.strftime('%Y-%m-%d %H:%M%z'),
            'Last-Translator': 'auto_translate <auto@example.com>',
            'Language-Team': 'auto_translate',
            'MIME-Version': '1.0',
            'Content-Type': 'text/plain; charset=UTF-8',
            'Content-Transfer-Encoding': '8bit',
        }
        return po

    def _chunk_list(self, lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

    def _compile_and_verify(self, locale_dir, target_lang):
        self.stdout.write('Compiling messages...')
        # Use Django's compilemessages command; it compiles all locales by default,
        # but we specify locale to restrict.
        call_command('compilemessages', locale=[target_lang], verbosity=0)
        mo_path = locale_dir / target_lang / 'LC_MESSAGES' / 'django.mo'
        if not mo_path.exists() or mo_path.stat().st_size == 0:
            raise CommandError(f'Compilation failed: {mo_path} does not exist or is empty.')
        self.stdout.write(self.style.SUCCESS(f'Compiled to {mo_path}'))

    def _print_strings(self, strings):
        if not strings:
            self.stdout.write('No strings to translate.')
            return
        self.stdout.write('Strings that would be sent for translation:')
        for s in strings:
            self.stdout.write(f'  - {s}')

    def _print_summary(self, total_detected, already_translated, sent, succeeded, failed,
                       po_path, mo_path, status):
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('TRANSLATION SUMMARY')
        self.stdout.write('=' * 50)
        self.stdout.write(f'Templates scanned: (see log above)')
        self.stdout.write(f'Strings detected: {total_detected}')
        self.stdout.write(f'Already translated: {already_translated}')
        self.stdout.write(f'Sent to Google: {sent}')
        self.stdout.write(f'Succeeded: {succeeded}')
        self.stdout.write(f'Failed: {failed}')
        self.stdout.write(f'PO file: {po_path}')
        if mo_path:
            self.stdout.write(f'MO file: {mo_path}')
        self.stdout.write(f'Status: {status}')
        self.stdout.write('=' * 50)


# ----------------------------------------------------------------------
# Utility functions (module-level)
# ----------------------------------------------------------------------
def extract_translatable_strings(template_dir):
    """
    Scan all .html files under template_dir and extract user-facing strings
    from {% trans %} and {% blocktrans %} tags.
    """
    strings = set()
    template_dir = Path(template_dir)

    # Regex for {% trans "string" %} or {% trans 'string' %}
    trans_pattern = re.compile(
        r'{%\s*trans\s+(?:"([^"]*)"|\'([^\']*)\')\s*(?:context\s+(?:"([^"]*)"|\'([^\']*)\'))?\s*%}'
    )
    # Regex for {% blocktrans %} ... {% endblocktrans %}
    blocktrans_pattern = re.compile(
        r'{%\s*blocktrans[^%]*%}(.*?){%\s*endblocktrans\s*%}',
        re.DOTALL
    )

    for template_file in template_dir.rglob('*.html'):
        try:
            content = template_file.read_text(encoding='utf-8')
        except Exception:
            continue

        # Extract trans tags
        for match in trans_pattern.finditer(content):
            string = match.group(1) or match.group(2)
            if string:
                strings.add(string)

        # Extract blocktrans bodies
        for match in blocktrans_pattern.finditer(content):
            body = match.group(1).strip()
            if body:
                strings.add(body)

    return list(strings)


def protect_placeholders(text):
    """
    Replace Django template variables like {{ var }} with placeholders
    to prevent the translation API from altering them.
    Returns (protected_text, mapping_dict).
    """
    mapping = {}
    def repl(match):
        index = len(mapping)
        placeholder = f'__PH{index}__'
        mapping[placeholder] = match.group(0)
        return placeholder
    protected = re.sub(r'\{\{.*?\}\}', repl, text)
    return protected, mapping


def unprotect_placeholders(text, mapping):
    """
    Replace placeholders back with original template variables.
    """
    for placeholder, original in mapping.items():
        text = text.replace(placeholder, original)
    return text


def translate_batch(client, project_id, contents, source_lang, target_lang):
    """Translate a list of strings using Google Cloud Translation v3."""
    parent = f"projects/{project_id}/locations/global"
    request = translate.TranslateTextRequest(
        parent=parent,
        contents=contents,
        source_language_code=source_lang,
        target_language_code=target_lang,
        mime_type="text/plain",
    )
    response = client.translate_text(request=request, retry=None)
    return [t.translated_text for t in response.translations]


def translate_with_retry(client, project_id, contents, source_lang, target_lang,
                         max_retries=5, backoff_factor=2):
    """
    Translate with exponential backoff on transient errors.
    Raises on permanent failure or after exhausting retries.
    """
    for attempt in range(max_retries):
        try:
            return translate_batch(client, project_id, contents, source_lang, target_lang)
        except google_exceptions.GoogleAPICallError as e:
            # InvalidArgument is permanent; do not retry
            if isinstance(e, google_exceptions.InvalidArgument):
                raise
            if attempt == max_retries - 1:
                raise
            sleep_time = backoff_factor ** attempt
            logger.warning(f'Transient error: {e}. Retrying in {sleep_time}s...')
            time.sleep(sleep_time)