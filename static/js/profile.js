const form = document.querySelector("#profile-form");

const username = document.querySelector("#username");
const first_name = document.querySelector("#first_name");
const last_name = document.querySelector("#last_name");
const email = document.querySelector("#email");
const avatar = document.querySelector("#avatar");

async function getDataProfile() {
    try {
        const response = await fetch(Url);

        if (!response.ok) {
            throw new Error("اطلاعات به درستی دریافت نشد");
        }

        const data = await response.json();

        const user__name = data.username;
        const first__name = data.first_name;
        const last__name = data.last_name;
        const email__address = data.email;
        const avatar__profile = data.avatar

        username.value = user__name;
        first_name.value = first__name;
        last_name.value = last__name;
        email.value = email__address;

        if (avatar__profile === null){
            return 
        }
        else {
            avatar.src = avatar__profile;
        }

    } catch (error) {
        console.error("Error:", error);
    }
}

getDataProfile();