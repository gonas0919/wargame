const sessionId = SERVER_USER_ID;

let currentUserHistory = [];

function updateUrlDisplay() {
    // Feature disabled: do not mutate the initial bot message
}

document.getElementById('payloadInput').addEventListener('input', updateUrlDisplay);

document.getElementById('payloadInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        sendPayload();
    }
});

function sendPayload() {
    const input = document.getElementById('payloadInput');
    const path = input.value.trim();
    
    if (!path) return;
    
    const fullUrl = `http://34.47.116.127:8080/${path}`;
    addMessage('user', fullUrl);
    currentPayload = path;
    input.value = '';
    updateUrlDisplay();
    
    setTimeout(() => {
        generateAIResponse(path);
    }, 500);
}

function addMessage(sender, content, actions = null) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const avatarText = sender === 'user' ? '나' : '영';
    const avatarClass = sender;
    
    let actionsHtml = '';
    if (actions) {
        actionsHtml = `
            <div class="message-actions">
                ${actions.map((action, index) => 
                    `<button class="action-btn ${action.class || ''}" data-action="${index}">
                        ${action.text}
                    </button>`
                ).join('')}
            </div>
        `;
    }
    
    messageDiv.innerHTML = `
        <div class="message-avatar ${avatarClass}">${avatarText}</div>
        <div class="message-content">
            <div class="message-text">$</div>
            ${actionsHtml}
        </div>
    `;
    const messageTextDiv = messageDiv.querySelector('.message-text');

if (sender === 'user') {
    messageTextDiv.textContent = content;
    } else {
    messageTextDiv.innerHTML = content;
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    

if (actions) {
        actions.forEach((action, index) => {
            const button = messageDiv.querySelector(`[data-action="${index}"]`);
            if (button) {
                button.addEventListener('click', () => {
                    if (action.actionType === 'openTab' && action.pathData) {
                        openInNewTab(action.pathData);
                    }
                });
            }
        });
    }
    
    currentUserHistory.push({ sender, content, timestamp: new Date() });
}

function generateAIResponse(path) {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message ai';
    typingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span>Analyzing...</span>
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('chatMessages').appendChild(typingDiv);
    document.getElementById('chatMessages').scrollTop = chatMessages.scrollHeight;
    
    setTimeout(() => {
        typingDiv.remove();
        
        let aiResponse;
        let actions = [];
        
        aiResponse = `"${escapeHtml(path)}" 이 주소는 뭐야? 들어가봤는데 아무것도 안 떠`;
        
        actions = [
            {
                text: '새 탭에서 열기',
                actionType: 'openTab',
                pathData: path,
                class: ''
            }
        ];
        
        addMessage('ai', aiResponse, actions);
    }, 1000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openInNewTab(path) {
    const fullUrl = `http://34.47.116.127:8080/${path}`;
    window.open(fullUrl, '_blank');
}

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('payloadInput').focus();
});