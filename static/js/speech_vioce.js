const nameInput = document.getElementById("id_name");
const voiceInput = document.getElementById("id_voies");
const textInput = document.getElementById("id_text");

const button = document.getElementById("transcribe-btn");

button.addEventListener("click", async () => {

    const file = voiceInput.files[0];

    if (!file) {
        alert("لطفاً فایل صوتی را انتخاب کنید.");
        return;
    }

    button.disabled = true;
    button.textContent = "در حال پردازش...";

    try {

        const result =
            await SpeechToText.transcribe(file, {
                language: "persian"
            });

        textInput.value = result.text;

    } catch (error) {

        console.error(error);

        alert(
            "تبدیل صدا به متن انجام نشد."
        );

    } finally {

        button.disabled = false;
        button.textContent = "تبدیل صدا به متن";

    }

});