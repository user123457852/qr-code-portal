// Mini base de dados
const usersDB = {
    "admin": "1234",
    "user1": "password1",
    "user2": "password2"
};

function validateLogin() {
    var user = document.getElementById("userInput").value;
    var password = document.getElementById("passwordInput").value;

    // Faz uma requisição para o backend Flask
    fetch("http://127.0.0.1:5000/api/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ 
            user_id: user, 
            password: password 
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Redireciona para a página do paciente após login bem-sucedido
            window.location.href = "patient_info.html";
        } else {
            // Exibe mensagem de erro
            document.getElementById("errorMessage").style.display = "block";
            document.getElementById("errorMessage").innerText = "Login inválido!";
        }
    })
    .catch(error => console.error("Erro ao conectar com o backend:", error));
}


// Função para navegar entre páginas
function navigateTo(page) {
    window.history.pushState({}, '', page);
    loadPage(page);
}

// Função para carregar a página
function loadPage(page) {
    const container = document.getElementById('app');
    fetch(page)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(html => {
            container.innerHTML = html;
        })
        .catch(err => {
            console.error('Error loading page:', err);
            navigateTo('error.html');
        });
}

// Gerencia o histórico de navegação
window.onpopstate = function(event) {
    loadPage(location.pathname);
};

// Iniciar a aplicação carregando a página inicial
document.addEventListener('DOMContentLoaded', function() {
    loadPage('index.html');
});
function fetchPatientData(patientId) {
    fetch(`http://127.0.0.1:5000/api/patients/${patientId}`)
    .then(response => response.json())
    .then(data => {
        document.getElementById("patientName").innerText = `${data.first_name} ${data.last_name}`;
        document.getElementById("diagnosis").innerText = data.diagnosis;
        document.getElementById("medication").innerText = data.medication;
        // Adicione mais campos conforme necessário
    })
    .catch(error => console.error("Erro ao buscar dados do paciente:", error));
}

// Chama a função automaticamente quando a página carregar
document.addEventListener("DOMContentLoaded", function() {
    const urlParams = new URLSearchParams(window.location.search);
    const patientId = urlParams.get("id"); // Obtém o ID do paciente da URL
    if (patientId) {
        fetchPatientData(patientId);
    }
});
