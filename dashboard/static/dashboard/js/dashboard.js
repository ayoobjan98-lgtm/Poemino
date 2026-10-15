(function () {
    'use strict';

    // ----- Theme -----
    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('dashboard-theme', theme);
        var iconClass = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
        document.querySelectorAll('#theme-icon, #sidebar-theme-icon, #theme-icon-text').forEach(function (icon) {
            icon.className = iconClass;
        });
    }

    function toggleTheme() {
        var current = document.documentElement.getAttribute('data-theme') || 'light';
        setTheme(current === 'dark' ? 'light' : 'dark');
    }

    // ----- Confirm modal -----
    var confirmResolve = null;
    var confirmModal = null;

    window.dashboardConfirm = function (message) {
        return new Promise(function (resolve) {
            var msgEl = document.getElementById('dashboardConfirmMessage');
            if (msgEl) msgEl.textContent = message;
            confirmResolve = resolve;
            if (confirmModal) confirmModal.show();
        });
    };

    // ----- Sidebar toggle -----
    function openSidebar() {
        var sidebarEl = document.getElementById('sidebar');
        var backdrop = document.getElementById('sidebar-backdrop');
        if (sidebarEl) sidebarEl.classList.add('show');
        if (backdrop) backdrop.style.display = 'block';
        console.log('Sidebar opened');
    }

    function closeSidebar() {
        var sidebarEl = document.getElementById('sidebar');
        var backdrop = document.getElementById('sidebar-backdrop');
        if (sidebarEl) sidebarEl.classList.remove('show');
        if (backdrop) backdrop.style.display = 'none';
        console.log('Sidebar closed');
    }

    document.addEventListener('DOMContentLoaded', function () {
        console.log('Dashboard JS loaded');

        // Theme init
        var current = document.documentElement.getAttribute('data-theme') || 'light';
        var iconClass = current === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
        document.querySelectorAll('#theme-icon, #sidebar-theme-icon, #theme-icon-text').forEach(function (icon) {
            icon.className = iconClass;
        });

        document.querySelectorAll('#theme-toggle, #sidebar-theme-toggle, #theme-toggle-text').forEach(function (btn) {
            btn.addEventListener('click', toggleTheme);
        });

        // Sidebar toggle button (hamburger)
        var toggleBtn = document.getElementById('sidebar-toggle-btn');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', openSidebar);
            console.log('Sidebar toggle button wired');
        } else {
            console.error('Sidebar toggle button (#sidebar-toggle-btn) not found');
        }

        // Sidebar close button (X inside sidebar)
        var closeBtn = document.getElementById('sidebar-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeSidebar);
        }

        // Backdrop
        var backdrop = document.getElementById('sidebar-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', closeSidebar);
        }

        // Alerts
        document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
            setTimeout(function () {
                var bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        });

        // Confirm modal setup
        var modalEl = document.getElementById('dashboardConfirmModal');
        if (modalEl) {
            confirmModal = new bootstrap.Modal(modalEl);
            document.getElementById('dashboardConfirmYes').addEventListener('click', function () {
                if (confirmResolve) confirmResolve(true);
                confirmModal.hide();
            });
            document.getElementById('dashboardConfirmCancel').addEventListener('click', function () {
                if (confirmResolve) confirmResolve(false);
                confirmModal.hide();
            });
            modalEl.addEventListener('hidden.bs.modal', function () {
                if (confirmResolve) confirmResolve(false);
            });
        }

        // data-confirm elements
        document.querySelectorAll('[data-confirm]').forEach(function (el) {
            if (el.hasAttribute('onclick') && el.getAttribute('onclick').indexOf('confirm(') !== -1) {
                el.removeAttribute('onclick');
            }
            if (el.tagName === 'FORM' && el.hasAttribute('onsubmit') && el.getAttribute('onsubmit').indexOf('confirm(') !== -1) {
                el.removeAttribute('onsubmit');
            }
            el.addEventListener('click', function (e) {
                e.preventDefault();
                var message = el.getAttribute('data-confirm') || 'Are you sure?';
                window.dashboardConfirm(message).then(function (confirmed) {
                    if (confirmed) {
                        if (el.tagName === 'A') {
                            window.location.href = el.getAttribute('href');
                        } else if (el.tagName === 'BUTTON' && el.form) {
                            el.form.submit();
                        } else {
                            el.removeEventListener('click', arguments.callee);
                            el.click();
                        }
                    }
                });
            });
        });

        // Intercept forms with onsubmit="return confirm(...)"
        document.querySelectorAll('form[onsubmit]').forEach(function (form) {
            var attr = form.getAttribute('onsubmit');
            if (attr.indexOf('confirm(') !== -1) {
                var msgMatch = attr.match(/confirm\(['"]([^'"]+)['"]/);
                var message = msgMatch ? msgMatch[1] : 'Are you sure?';
                form.removeAttribute('onsubmit');
                form.addEventListener('submit', function (e) {
                    e.preventDefault();
                    window.dashboardConfirm(message).then(function (confirmed) {
                        if (confirmed) {
                            form.submit();
                        }
                    });
                });
            }
        });
    });
})();