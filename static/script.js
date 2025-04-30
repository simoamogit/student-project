// Animazione al caricamento
document.addEventListener('DOMContentLoaded', () => {
    // Effetto hover avanzato
    const badges = document.querySelectorAll('.badge');
    badges.forEach(badge => {
        badge.addEventListener('mouseenter', () => {
            badge.style.transform = 'scale(1.1)';
        });
        badge.addEventListener('mouseleave', () => {
            badge.style.transform = 'scale(1)';
        });
    });
    
    // Animazione tabelle
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach((row, index) => {
        row.style.animationDelay = `${index * 0.1}s`;
    });
});

document.querySelector('form').addEventListener('submit', function(event) {
    const voto = parseFloat(document.querySelector('[name="voto"]').value);
    if (voto < 0 || voto > 10 || isNaN(voto)) {
        alert("Il voto deve essere tra 0 e 10!");
        event.preventDefault(); // Impedisce l'invio del form
    }
});

// Funzione per inizializzare i gestori eventi per i bottoni di eliminazione
document.addEventListener('DOMContentLoaded', function() {
    // Aggiungi gestori eventi a tutti i bottoni di eliminazione esistenti
    inizializzaBottoniElimina();
});

function inizializzaBottoniElimina() {
    // Seleziona tutti i bottoni di eliminazione
    const bottoniElimina = document.querySelectorAll('.btn-elimina');
    
    // Aggiungi event listener a ciascun bottone
    bottoniElimina.forEach(bottone => {
        bottone.addEventListener('click', eliminaVoto);
    });
}

// Funzione per gestire il click sul bottone elimina
function eliminaVoto(event) {
    // Ottieni l'elemento del voto (il genitore del bottone cliccato)
    const votoElement = event.target.closest('.voto-item');
    
    // Ottieni l'ID del voto
    const votoId = votoElement.dataset.id;
    
    // Chiedi conferma all'utente
    if (window.confirm("Sei sicuro di voler eliminare questo voto?")) {
        // Invia richiesta DELETE al backend
        fetch(`/api/voti/${votoId}`, {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json"
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Rimuovi l'elemento dalla pagina
                votoElement.remove();
                // Opzionale: mostra un messaggio di successo
                mostraMessaggio("Voto eliminato con successo", "success");
            } else {
                // Mostra messaggio di errore
                mostraMessaggio(data.error || "Errore durante l'eliminazione", "error");
            }
        })
        .catch(error => {
            console.error("Errore durante l'eliminazione del voto:", error);
            mostraMessaggio("Si è verificato un errore durante l'eliminazione", "error");
        });
    }
}

// Funzione per mostrare messaggi di feedback all'utente
function mostraMessaggio(testo, tipo) {
    // Crea elemento messaggio
    const messaggio = document.createElement('div');
    messaggio.className = `messaggio ${tipo}`;
    messaggio.textContent = testo;
    
    // Aggiungi al DOM
    const container = document.querySelector('.container') || document.body;
    container.prepend(messaggio);
    
    // Rimuovi dopo 3 secondi
    setTimeout(() => {
        messaggio.remove();
    }, 3000);
}

// Se aggiungi nuovi voti dinamicamente, puoi chiamare questa funzione per reinizializzare i bottoni
function aggiornaGestoriEventi() {
    inizializzaBottoniElimina();
}

// Funzione per inizializzare i gestori eventi per i bottoni di eliminazione
document.addEventListener('DOMContentLoaded', function() {
    // Aggiungi gestori eventi a tutti i bottoni di eliminazione esistenti
    inizializzaBottoniElimina();
});

function inizializzaBottoniElimina() {
    // Seleziona tutti i bottoni di eliminazione
    const bottoniElimina = document.querySelectorAll('.btn-elimina');
    
    // Aggiungi event listener a ciascun bottone
    bottoniElimina.forEach(bottone => {
        bottone.addEventListener('click', eliminaVoto);
    });
}

// Funzione per gestire il click sul bottone elimina
function eliminaVoto(event) {
    // Ottieni l'elemento del voto (il genitore del bottone cliccato)
    const votoElement = event.target.closest('.voto-item');
    
    // Ottieni l'ID del voto
    const votoId = votoElement.dataset.id;
    
    // Chiedi conferma all'utente
    if (window.confirm("Sei sicuro di voler eliminare questo voto?")) {
        // Invia richiesta DELETE al backend
        fetch(`/api/voti/${votoId}`, {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json"
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Rimuovi l'elemento dalla pagina
                votoElement.remove();
                // Opzionale: mostra un messaggio di successo
                mostraMessaggio("Voto eliminato con successo", "success");
            } else {
                // Mostra messaggio di errore
                mostraMessaggio(data.error || "Errore durante l'eliminazione", "error");
            }
        })
        .catch(error => {
            console.error("Errore durante l'eliminazione del voto:", error);
            mostraMessaggio("Si è verificato un errore durante l'eliminazione", "error");
        });
    }
}

// Funzione per mostrare messaggi di feedback all'utente
function mostraMessaggio(testo, tipo) {
    // Crea elemento messaggio
    const messaggio = document.createElement('div');
    messaggio.className = `messaggio ${tipo}`;
    messaggio.textContent = testo;
    
    // Aggiungi al DOM
    const container = document.querySelector('.container') || document.body;
    container.prepend(messaggio);
    
    // Rimuovi dopo 3 secondi
    setTimeout(() => {
        messaggio.remove();
    }, 3000);
}

// Se aggiungi nuovi voti dinamicamente, puoi chiamare questa funzione per reinizializzare i bottoni
function aggiornaGestoriEventi() {
    inizializzaBottoniElimina();
}