const inputs = document.querySelectorAll(".input");

function addcl() {
    let parent = this.parentNode.parentNode;
    parent.classList.add("focus");
}

function remcl() {
    let parent = this.parentNode.parentNode;
    if (this.value == "") {
        parent.classList.remove("focus");
    }
}

inputs.forEach(input => {
    input.addEventListener("focus", addcl);
    input.addEventListener("blur", remcl);
});

const passwordInput = document.getElementById("password");
const lengthRequirement = document.getElementById("length");
const uppercaseRequirement = document.getElementById("uppercase");
const lowercaseRequirement = document.getElementById("lowercase");
const numberRequirement = document.getElementById("number");
const specialRequirement = document.getElementById("special");

passwordInput.addEventListener("input", function() {
    const password = this.value;

    // Verificar requisitos
    const hasLength = password.length >= 8 && password.length < 15;
    const hasUppercase = /[A-Z]/.test(password);
    const hasLowercase = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);

    // Actualizar el estado de los requisitos
    lengthRequirement.className = hasLength ? "requirement valid" : "requirement";
    uppercaseRequirement.className = hasUppercase ? "requirement valid" : "requirement";
    lowercaseRequirement.className = hasLowercase ? "requirement valid" : "requirement";
    numberRequirement.className = hasNumber ? "requirement valid" : "requirement";
    specialRequirement.className = hasSpecial ? "requirement valid" : "requirement";
});
// Función para mostrar el modal con un mensaje
function showModal(message) {
    document.getElementById('errorMessage').innerText = message;
    const modal = document.getElementById('errorModal');
    modal.classList.add('show'); // Agrega la clase para mostrar el modal
    modal.style.display = "block"; // Muestra el modal
}

function closeModal() {
    const modal = document.getElementById('errorModal');
    modal.classList.remove('show'); // Quita la clase para ocultar el modal
    setTimeout(() => {
        modal.style.display = "none"; // Oculta el modal después de la animación
    }, 300); // Tiempo de la animación
}

// Cerrar el modal si se hace clic fuera de él
window.onclick = function(event) {
    if (event.target == document.getElementById('errorModal')) {
        closeModal();
    }
}