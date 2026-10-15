// static/js/home.js

document.addEventListener("DOMContentLoaded", function () {
    const poetryGrid = document.getElementById("poetryGrid");
    const poemsLoading = document.getElementById("poemsLoading");
    const poemsEmpty = document.getElementById("poemsEmpty");
    const poemsError = document.getElementById("poemsError");

    if (!poetryGrid) {
        console.error("poetryGrid not found.");
        return;
    }

    /*
     * ---------------------------------------------------------
     * UI HELPERS
     * ---------------------------------------------------------
     */

    function showElement(element) {
        if (element) {
            element.classList.remove("d-none");
        }
    }

    function hideElement(element) {
        if (element) {
            element.classList.add("d-none");
        }
    }

    /*
     * ---------------------------------------------------------
     * TRANSLATIONS
     * ---------------------------------------------------------
     */

    function getTranslation(key, fallback) {
        if (
            window.POEM_TRANSLATIONS &&
            Object.prototype.hasOwnProperty.call(
                window.POEM_TRANSLATIONS,
                key
            )
        ) {
            return window.POEM_TRANSLATIONS[key];
        }

        return fallback;
    }

    /*
     * ---------------------------------------------------------
     * AUTHOR
     * ---------------------------------------------------------
     */

    function getAuthorName(author) {
        if (!author) {
            return getTranslation("master", "Master");
        }

        const firstName = String(
            author.first_name || ""
        ).trim();

        const lastName = String(
            author.last_name || ""
        ).trim();

        const master = getTranslation(
            "master",
            "Master"
        );

        if (firstName && lastName) {
            return `${master} ${firstName} ${lastName}`;
        }

        if (firstName) {
            return `${master} ${firstName}`;
        }

        if (lastName) {
            return `${master} ${lastName}`;
        }

        const fallbackName =
            author.username ||
            "ناشناس";

        return `${master} ${fallbackName}`;
    }

    function createAuthorAvatar(author) {
        const wrapper =
            document.createElement("div");

        /*
         * Avatar
         */

        if (
            author &&
            author.avatar
        ) {
            const image =
                document.createElement("img");

            image.src = author.avatar;

            image.alt = getTranslation(
                "authorAvatar",
                "Author Avatar"
            );

            image.className =
                "rounded-circle flex-shrink-0";

            image.width = 48;
            image.height = 48;

            image.style.objectFit = "cover";

            image.addEventListener(
                "error",
                function () {
                    wrapper.innerHTML = "";

                    wrapper.appendChild(
                        createFallbackAvatar()
                    );
                }
            );

            wrapper.appendChild(image);

            return wrapper;
        }

        /*
         * Fallback
         */

        wrapper.appendChild(
            createFallbackAvatar()
        );

        return wrapper;
    }

    function createFallbackAvatar() {
        const fallback =
            document.createElement("div");

        fallback.className =
            "d-flex align-items-center justify-content-center rounded-circle flex-shrink-0";

        fallback.style.width = "48px";
        fallback.style.height = "48px";
        fallback.style.background =
            "rgba(255,255,255,.06)";

        const icon =
            document.createElement("i");

        icon.className =
            "bi bi-person-circle text-info fs-5";

        fallback.appendChild(icon);

        return fallback;
    }

    /*
     * ---------------------------------------------------------
     * POEM TEXT
     * ---------------------------------------------------------
     */

    function createShortPoemText(text) {
        const normalizedText =
            String(text || "").trim();

        if (!normalizedText) {
            return "";
        }

        const words =
            normalizedText.split(/\s+/);

        let shortText =
            words
                .slice(0, 20)
                .join(" ");

        if (words.length > 20) {
            shortText += "...";
        }

        return shortText;
    }

    /*
     * ---------------------------------------------------------
     * POEM CARD
     * ---------------------------------------------------------
     */

    function createPoemCard(
        poem,
        index
    ) {
        const article =
            document.createElement("article");

        article.className =
            "poem-card";

        article.style.setProperty(
            "--i",
            index
        );

        /*
         * Accent
         */

        const accent =
            document.createElement("div");

        accent.className =
            "card-accent";

        article.appendChild(accent);

        /*
         * Number
         */

        const number =
            document.createElement("span");

        number.className =
            "poem-number";

        number.textContent =
            `#${index + 1}`;

        article.appendChild(number);

        /*
         * Title
         */

        const title =
            document.createElement("h3");

        title.className =
            "poem-title";

        const poemName =
            String(
                poem.name ||
                poem.text ||
                getTranslation(
                    "noPoems",
                    "No poems found."
                )
            );

        title.textContent =
            poemName.length > 40
                ? `${poemName.substring(
                    0,
                    40
                )}...`
                : poemName;

        article.appendChild(title);

        /*
         * Poem text
         */

        const textWrapper =
            document.createElement("div");

        textWrapper.className =
            "poem-text-wrapper";

        const details =
            document.createElement("details");

        const summary =
            document.createElement("summary");

        summary.textContent =
            getTranslation(
                "poemText",
                "Poem Text"
            );

        details.appendChild(summary);

        const poemText =
            document.createElement("div");

        poemText.className =
            "poem-text";

        const shortText =
            createShortPoemText(
                poem.text
            );

        poemText.appendChild(
            document.createTextNode(
                shortText
                    ? `${shortText} `
                    : ""
            )
        );

        /*
         * Detail link
         */

        if (
            poem.id !== undefined &&
            poem.id !== null
        ) {
            const detailLink =
                document.createElement("a");

            detailLink.href =
                `/poem/${encodeURIComponent(
                    poem.id
                )}/`;

            detailLink.className =
                "text-decoration-none text-info";

            detailLink.textContent =
                getTranslation(
                    "detailPoem",
                    "Detail Poem"
                );

            poemText.appendChild(
                detailLink
            );
        }

        details.appendChild(
            poemText
        );

        textWrapper.appendChild(
            details
        );

        article.appendChild(
            textWrapper
        );

        /*
         * -----------------------------------------------------
         * AUTHOR SECTION
         * -----------------------------------------------------
         */

        const authorSection =
            document.createElement("div");

        authorSection.className =
            "mt-4 pt-3 border-top border-secondary-subtle";

        const authorRow =
            document.createElement("div");

        authorRow.className =
            "d-flex align-items-center gap-3";

        /*
         * Avatar
         */

        authorRow.appendChild(
            createAuthorAvatar(
                poem.author
            )
        );

        /*
         * Author information
         */

        const authorInfo =
            document.createElement("div");

        authorInfo.className =
            "min-w-0";

        const authorLabel =
            document.createElement("div");

        authorLabel.className =
            "small text-white-50 mb-1";

        authorLabel.textContent =
            getTranslation(
                "author",
                "Author"
            );

        const authorName =
            document.createElement("div");

        authorName.className =
            "text-white fw-semibold text-truncate";

        authorName.textContent =
            getAuthorName(
                poem.author
            );

        authorInfo.appendChild(
            authorLabel
        );

        authorInfo.appendChild(
            authorName
        );

        authorRow.appendChild(
            authorInfo
        );

        authorSection.appendChild(
            authorRow
        );

        article.appendChild(
            authorSection
        );

        /*
         * -----------------------------------------------------
         * DATES
         * -----------------------------------------------------
         */

        if (
            poem.created_at ||
            poem.edited_at
        ) {
            const dateSection =
                document.createElement("div");

            dateSection.className =
                "mt-3 pt-3 border-top border-secondary-subtle";

            const row =
                document.createElement("div");

            row.className =
                "row g-3";

            /*
             * Created
             */

            if (poem.created_at) {
                const createdCol =
                    document.createElement("div");

                createdCol.className =
                    "col-12 col-sm-6";

                const createdLabel =
                    document.createElement("div");

                createdLabel.className =
                    "small text-white-50 mb-1";

                const createdIcon =
                    document.createElement("i");

                createdIcon.className =
                    "bi bi-calendar-plus me-1";

                createdLabel.appendChild(
                    createdIcon
                );

                createdLabel.appendChild(
                    document.createTextNode(
                        getTranslation(
                            "created",
                            "Created"
                        )
                    )
                );

                const createdValue =
                    document.createElement("div");

                createdValue.className =
                    "small text-white";

                createdValue.textContent =
                    poem.created_at;

                createdCol.appendChild(
                    createdLabel
                );

                createdCol.appendChild(
                    createdValue
                );

                row.appendChild(
                    createdCol
                );
            }

            /*
             * Edited
             */

            if (poem.edited_at) {
                const editedCol =
                    document.createElement("div");

                editedCol.className =
                    "col-12 col-sm-6";

                const editedLabel =
                    document.createElement("div");

                editedLabel.className =
                    "small text-white-50 mb-1";

                const editedIcon =
                    document.createElement("i");

                editedIcon.className =
                    "bi bi-calendar-check me-1";

                editedLabel.appendChild(
                    editedIcon
                );

                editedLabel.appendChild(
                    document.createTextNode(
                        getTranslation(
                            "lastEdited",
                            "Last Edited"
                        )
                    )
                );

                const editedValue =
                    document.createElement("div");

                editedValue.className =
                    "small text-white";

                editedValue.textContent =
                    poem.edited_at;

                editedCol.appendChild(
                    editedLabel
                );

                editedCol.appendChild(
                    editedValue
                );

                row.appendChild(
                    editedCol
                );
            }

            dateSection.appendChild(
                row
            );

            article.appendChild(
                dateSection
            );
        }

        /*
         * -----------------------------------------------------
         * ANIMATION / VISIBILITY
         * -----------------------------------------------------
         */

        article.style.opacity = "1";
        article.style.visibility = "visible";
        article.style.display = "block";
        article.style.transform = "none";

        return article;
    }

    /*
     * ---------------------------------------------------------
     * API URL
     * ---------------------------------------------------------
     *
     * URL صفحه:
     *
     * /?poem_date=1405%2F05%2F08
     *
     * تبدیل می‌شود به:
     *
     * /0.1/poems/?poem_date=1405%2F05%2F08
     *
     * filter_type_ui فقط برای رابط کاربری است
     * و نباید به API ارسال شود.
     * ---------------------------------------------------------
     */

    function getApiUrl() {
        if (
            typeof POEMS_API_URL ===
            "undefined"
        ) {
            throw new Error(
                "POEMS_API_URL is not defined."
            );
        }

        const apiUrl =
            new URL(
                POEMS_API_URL,
                window.location.origin
            );

        const pageParams =
            new URLSearchParams(
                window.location.search
            );

        const filterNames = [
            "q",
            "author",
            "title",
            "poem_type",
            "poem_date",
            "status"
        ];

        filterNames.forEach(
            function (name) {
                const values =
                    pageParams.getAll(name);

                if (!values.length) {
                    return;
                }

                const value =
                    values[values.length - 1]
                        .trim();

                if (!value) {
                    return;
                }

                /*
                 * set() باعث می‌شود فقط یک
                 * مقدار برای هر فیلتر ارسال شود.
                 */

                apiUrl.searchParams.set(
                    name,
                    value
                );
            }
        );

        /*
         * اطمینان از حذف پارامتر UI
         */

        apiUrl.searchParams.delete(
            "filter_type_ui"
        );

        return apiUrl.toString();
    }

    /*
     * ---------------------------------------------------------
     * LOAD POEMS
     * ---------------------------------------------------------
     */

    async function loadPoems() {
        hideElement(
            poemsEmpty
        );

        hideElement(
            poemsError
        );

        showElement(
            poemsLoading
        );

        poetryGrid.innerHTML = "";

        try {
            const apiUrl =
                getApiUrl();

            console.log(
                "Poems API URL:",
                apiUrl
            );

            /*
             * دریافت اطلاعات از API
             */

            const response =
                await fetch(
                    apiUrl,
                    {
                        method: "GET",

                        headers: {
                            "Accept":
                                "application/json"
                        },

                        credentials:
                            "same-origin"
                    }
                );

            /*
             * HTTP Error
             */

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}`
                );
            }

            /*
             * JSON
             */

            const data =
                await response.json();

            console.log(
                "Poems API response:",
                data
            );

            /*
             * -------------------------------------------------
             * پشتیبانی از دو نوع response
             * -------------------------------------------------
             *
             * حالت اول:
             *
             * [
             *     {...},
             *     {...}
             * ]
             *
             * حالت دوم:
             *
             * {
             *     count: 3,
             *     next: null,
             *     previous: null,
             *     results: [...]
             * }
             */

            let poems = [];

            if (
                Array.isArray(data)
            ) {
                poems = data;
            } else if (
                data &&
                Array.isArray(
                    data.results
                )
            ) {
                poems =
                    data.results;
            }

            hideElement(
                poemsLoading
            );

            /*
             * هیچ شعری پیدا نشد
             */

            if (
                poems.length === 0
            ) {
                showElement(
                    poemsEmpty
                );

                return;
            }

            /*
             * ساخت کارت‌ها
             */

            poems.forEach(
                function (
                    poem,
                    index
                ) {
                    const card =
                        createPoemCard(
                            poem,
                            index
                        );

                    poetryGrid.appendChild(
                        card
                    );

                    /*
                     * Animation
                     */

                    requestAnimationFrame(
                        function () {
                            card.classList.add(
                                "is-visible"
                            );

                            card.style.opacity =
                                "1";

                            card.style.visibility =
                                "visible";

                            card.style.display =
                                "block";

                            card.style.transform =
                                "none";
                        }
                    );
                }
            );

        } catch (error) {
            console.error(
                "Failed to load poems:",
                error
            );

            hideElement(
                poemsLoading
            );

            /*
             * Error UI
             */

            if (poemsError) {
                poemsError.textContent =
                    getTranslation(
                        "loadError",
                        "خطا در دریافت شعرها. لطفاً دوباره تلاش کنید."
                    );

                showElement(
                    poemsError
                );
            }
        }
    }

    /*
     * ---------------------------------------------------------
     * START
     * ---------------------------------------------------------
     */

    loadPoems();
});

// END