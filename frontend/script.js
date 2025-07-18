let token = null;
let activeQuest = null;

async function createUser() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const resp = await fetch('/api/users/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name: email })
    });
    const data = await resp.json();
    document.getElementById('user-result').textContent = JSON.stringify(data, null, 2);
}

async function login() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);
    const resp = await fetch('/api/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params
    });
    const data = await resp.json();
    token = data.access_token;
    document.getElementById('user-result').textContent = 'Logged in';
}

async function submitGoal() {
    const goalText = document.getElementById('goal').value;
    const resp = await fetch('/api/goals/parse', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ goal: goalText })
    });
    const data = await resp.json();
    activeQuest = data;
    document.getElementById('quest-display').textContent = `${data.name}: ${data.description}`;
    document.getElementById('active-quest').textContent = `${data.name}: ${data.description}`;
}

async function submitAccomplishment() {
    if (!activeQuest) return;
    const description = document.getElementById('accomplishment').value;
    const resp = await fetch('/api/accomplishments/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name: 'Accomplishment', description, quest_id: activeQuest.id })
    });
    const data = await resp.json();
    document.getElementById('accomplishment-result').textContent = JSON.stringify(data, null, 2);
    const accId = data.accomplishment.id;
    const vcResp = await fetch(`/api/accomplishments/${accId}/issue-credential`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const vcData = await vcResp.json();
    document.getElementById('vc-display').textContent = vcData.verifiable_credential_jwt;
}

document.getElementById('register-btn').addEventListener('click', createUser);
document.getElementById('login-btn').addEventListener('click', login);
document.getElementById('submit-goal').addEventListener('click', submitGoal);
document.getElementById('submit-accomplishment').addEventListener('click', submitAccomplishment);
