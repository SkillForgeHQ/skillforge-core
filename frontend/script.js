document.getElementById('submit-goal').addEventListener('click', () => {
    const goal = document.getElementById('goal-input').value;
    fetch('/goals/parse', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: goal })
    })
    .then(response => response.json())
    .then(data => {
        const questDisplay = document.getElementById('quest-display');
        questDisplay.innerHTML = `
            <h2>${data.name}</h2>
            <p>${data.description}</p>
        `;
    })
    .catch(error => console.error('Error:', error));
});
