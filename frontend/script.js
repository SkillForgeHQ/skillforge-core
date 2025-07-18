let token = null;
let activeQuest = null;
let questPlan = [];
let currentQuestIndex = 0;

function renderQuestList() {
    const listEl = document.getElementById('quest-list');
    if (!listEl) return;
    listEl.innerHTML = '';

    questPlan.forEach((quest, idx) => {
        const li = document.createElement('li');
        li.textContent = `${quest.title}: ${quest.description}`;

        if (idx < currentQuestIndex) {
            li.classList.add('completed');
        } else if (idx === currentQuestIndex) {
            li.classList.add('active');
        } else {
            li.classList.add('future');
        }

        listEl.appendChild(li);
    });
}

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

    // Determine where the goal and quest information is located in the response
    let planJson = null;
    if (data.full_plan_json) {
        planJson = data.full_plan_json;
        activeQuest = data.first_quest || {
            id: data.id,
            name: data.name,
            description: data.description,
        };
    } else if (data.goal) {
        planJson = data.goal.full_plan_json;
        activeQuest = data.quest || data.goal.first_quest;
    } else {
        activeQuest = data;
    }

    try {
        questPlan = JSON.parse(planJson);
    } catch (e) {
        questPlan = [];
    }
    currentQuestIndex = 0;

    document.getElementById('quest-display').textContent = activeQuest ? `${activeQuest.name}: ${activeQuest.description}` : '';
    document.getElementById('active-quest').textContent = activeQuest ? `${activeQuest.name}: ${activeQuest.description}` : '';
    renderQuestList();
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

    // Update quest list UI to mark progress
    if (currentQuestIndex < questPlan.length - 1) {
        currentQuestIndex += 1;
        const nextQuest = questPlan[currentQuestIndex];
        document.getElementById('active-quest').textContent = `${nextQuest.title}: ${nextQuest.description}`;
    }
    renderQuestList();
}

document.getElementById('register-btn').addEventListener('click', createUser);
document.getElementById('login-btn').addEventListener('click', login);
document.getElementById('submit-goal').addEventListener('click', submitGoal);
document.getElementById('submit-accomplishment').addEventListener('click', submitAccomplishment);
