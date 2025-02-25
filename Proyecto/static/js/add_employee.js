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
