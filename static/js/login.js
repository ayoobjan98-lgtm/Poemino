async function getAPIToken() {
    const response = await fetch(Url_data, {
        method: "POST",
        credentials: "same-origin",
        headers: {
            "X-CSRFToken": getCSRFToken(),
            "X-Requested-With": "XMLHttpRequest"
        }
    });

    if (!response.ok) {
        throw new Error("Unable to create API token.");
    }

    const data = await response.json();

    sessionStorage.setItem(
        "api_access_token",
        data.access
    );

    sessionStorage.setItem(
        "api_token_type",
        data.token_type
    );

    sessionStorage.setItem(
        "api_role",
        data.role
    );

    sessionStorage.setItem(
        "api_expires_at",
        String(data.expires_at)
    );

    scheduleTokenExpiration(data.expires_at);

    return data;
}


/* =========================================================
   CSRF
========================================================= */

function getCSRFToken() {
    const csrfInput = document.querySelector(
        "#login-form input[name='csrfmiddlewaretoken']"
    );

    if (!csrfInput) {
        return "";
    }

    return csrfInput.value;
}


/* =========================================================
   TOKEN EXPIRATION
========================================================= */

function scheduleTokenExpiration(expiresAt) {
    const expirationTime =
        Number(expiresAt) * 1000;

    const delay =
        expirationTime - Date.now();

    if (delay <= 0) {
        logoutUser();
        return;
    }

    setTimeout(
        logoutUser,
        delay
    );
}


/* =========================================================
   LOGOUT
========================================================= */

async function logoutUser() {
    sessionStorage.removeItem(
        "api_access_token"
    );

    sessionStorage.removeItem(
        "api_token_type"
    );

    sessionStorage.removeItem(
        "api_role"
    );

    sessionStorage.removeItem(
        "api_expires_at"
    );

    window.location.href =
        "{% url 'login' %}";
}
