function showRulesModal() {
    const modal = document.getElementById('rulesModal');
    if (modal) modal.style.display = 'flex';
}

function closeRules() {
    const modal = document.getElementById('rulesModal');
    if (modal) modal.style.display = 'none';
    fetch('/choose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'close_rules' })
    });
}

function viewRules() {
    showRulesModal();
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function linesToParagraphs(text) {
    return String(text ?? '')
        .split('\n')
        .map(line => `<p>${escapeHtml(line)}</p>`)
        .join('');
}

function viewNotes() {
    fetch('/notes')
        .then(res => res.json())
        .then(data => {
            const content = document.getElementById('notesContent');
            let html = '';

            if (data.collected === 0) {
                html = '<p class="no-notes">尚未收集到任何信息碎片。</p>' +
                       '<p class="no-notes-hint">关键选择会留下记录，错误选择也会。</p>';
            }

            for (const [id, frag] of Object.entries(data.fragments).sort((a, b) => Number(a[0]) - Number(b[0]))) {
                html += `
                    <div class="note-fragment">
                        <div class="note-header">
                            <span class="note-number">碎片 #${escapeHtml(id)}</span>
                            <span class="note-name">${escapeHtml(frag.name)}</span>
                        </div>
                        <p class="note-text">${escapeHtml(frag.content)}</p>
                    </div>`;
            }

            for (let i = 1; i <= data.total; i++) {
                if (!data.fragments[i]) {
                    html += `
                        <div class="note-fragment missing">
                            <div class="note-header">
                                <span class="note-number">碎片 #${i}</span>
                                <span class="note-name">???</span>
                            </div>
                            <p class="note-text missing-text">[ 尚未发现 ]</p>
                        </div>`;
                }
            }

            content.innerHTML = html;
            document.getElementById('notesModal').style.display = 'flex';
        });
}

function closeNotes() {
    const modal = document.getElementById('notesModal');
    if (modal) modal.style.display = 'none';
}

function makeChoice(choiceIndex) {
    const buttons = document.querySelectorAll('#choicesBlock .choice-btn');
    buttons.forEach(btn => btn.disabled = true);
    document.body.classList.add('is-resolving');

    fetch('/choose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            type: 'event',
            choice_index: choiceIndex
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status !== 'ok') {
            console.error('Error:', data.message);
            buttons.forEach(btn => btn.disabled = false);
            document.body.classList.remove('is-resolving');
            return;
        }

        switch (data.outcome) {
            case 'death':
                handleDeath(data);
                break;
            case 'assimilation':
                handleAssimilation(data);
                break;
            case 'reset_s1':
                handleReset(data);
                break;
            case 'continue':
            case 'ending':
            default:
                handleContinue(data);
        }
    })
    .catch(err => {
        console.error('Request failed:', err);
        buttons.forEach(btn => btn.disabled = false);
        document.body.classList.remove('is-resolving');
        showToast('连接中断。疗养院暂时没有回应。');
    });
}

function openRitualModal() {
    const option = document.getElementById('noCostOption');
    const desc = option?.querySelector('.no-cost-desc')?.textContent?.trim();
    const action = option?.querySelector('.no-cost-btn span')?.textContent?.trim();
    const modal = document.getElementById('ritualModal');
    const descEl = document.getElementById('ritualDesc');
    const actionEl = document.getElementById('ritualAction');

    if (descEl && desc) descEl.textContent = desc;
    if (actionEl && action) actionEl.textContent = action;
    if (modal) modal.style.display = 'flex';
}

function closeRitualModal() {
    const modal = document.getElementById('ritualModal');
    if (modal) modal.style.display = 'none';
}

function triggerNoCost() {
    const ritualButtons = document.querySelectorAll('#ritualModal .choice-btn');
    ritualButtons.forEach(btn => btn.disabled = true);

    fetch('/choose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'no_cost' })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'ok') {
            updateErosionDisplay(data.new_erosion);
            closeRitualModal();
            ritualButtons.forEach(btn => btn.disabled = false);
            const noCostDiv = document.getElementById('noCostOption');
            if (noCostDiv) noCostDiv.style.display = 'none';
            if (data.consequence) appendConsequence(data.consequence);
            showToast('清醒记录已封存。');
        } else {
            ritualButtons.forEach(btn => btn.disabled = false);
        }
    });
}

function handleAssimilation(data) {
    updateErosionDisplay(data.new_erosion ?? 100);
    if (data.consequence) appendConsequence(data.consequence);

    const modal = document.getElementById('assimilationModal');
    const textEl = document.getElementById('assimilationText');
    const endingText = data.ending_data?.text || '你的记录被疗养院接管。所有规则开始以你的笔迹重写。';
    const lines = [data.consequence, endingText.split('\n').find(Boolean)]
        .filter(Boolean)
        .join('\n');

    if (textEl) textEl.innerHTML = linesToParagraphs(lines);
    if (modal) modal.style.display = 'flex';
    document.body.classList.remove('is-resolving');
    document.body.classList.add('assimilation-lock');

    setTimeout(() => { window.location.href = '/ending'; }, 3200);
}

function handleDeath(data) {
    const modal = document.getElementById('deathModal');
    document.getElementById('deathTitle').textContent = `【${data.be_title}】`;
    document.getElementById('deathText').innerHTML = linesToParagraphs(data.be_text);
    modal.style.display = 'flex';
    document.body.classList.remove('is-resolving');
}

function retryFromEvent() {
    fetch('/retry', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') location.reload();
        });
}

function loadLastSave() {
    fetch('/load_last_save', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') location.reload();
        });
}

function handleContinue(data) {
    if (data.new_erosion !== undefined) updateErosionDisplay(data.new_erosion);
    if (data.new_fragments && data.new_fragments.length > 0) showFragmentToast(data.new_fragments, data.total_fragments);
    if (data.consequence) appendConsequence(data.consequence);

    if (data.scene_complete) {
        if (data.ending_data) {
            setTimeout(() => { window.location.href = '/ending'; }, 2000);
        } else if (data.completion_text) {
            showTransition(data.completion_text);
        }
    } else if (data.ending_data) {
        setTimeout(() => { window.location.href = '/ending'; }, 1500);
    } else {
        if (data.show_no_cost) showNoCostOption(data.no_cost_desc, data.no_cost_option);
        setTimeout(() => location.reload(), 650);
    }
}

function handleReset(data) {
    updateErosionDisplay(data.new_erosion);
    if (data.consequence) appendConsequence(data.consequence);
    showRecovery(data.consequence);
}

function showTransition(text) {
    const modal = document.getElementById('transitionModal');
    const label = document.getElementById('transitionLabel');
    const button = document.getElementById('transitionButton');
    if (label) label.textContent = 'AREA SEALED';
    if (button) button.textContent = '推开下一扇门';
    document.getElementById('transitionText').innerHTML = linesToParagraphs(text);
    modal.style.display = 'flex';
}

function showRecovery(text) {
    const modal = document.getElementById('transitionModal');
    const label = document.getElementById('transitionLabel');
    const button = document.getElementById('transitionButton');
    if (label) label.textContent = 'SEDATION RECALL';
    if (button) button.textContent = '在病房醒来';
    document.getElementById('transitionText').innerHTML = linesToParagraphs((text || '') + '\n\n灯管重新亮起。你被放回第一间病房，只有记录没有倒退。');
    modal.style.display = 'flex';
}

function continueToNextScene() {
    document.getElementById('transitionModal').style.display = 'none';
    location.reload();
}

function updateErosionDisplay(newErosion) {
    const fillEl = document.querySelector('.erosion-bar-fill');
    const valueEl = document.querySelector('.erosion-value');
    const stateEl = document.querySelector('.erosion-state-name');

    let color;
    let stateName;
    let bodyClass;
    if (newErosion <= 20) {
        color = '#79b86b'; stateName = '正常'; bodyClass = 'normal';
    } else if (newErosion <= 40) {
        color = '#c8a94b'; stateName = '轻度侵蚀'; bodyClass = 'mild';
    } else if (newErosion <= 60) {
        color = '#c4773d'; stateName = '中度侵蚀'; bodyClass = 'moderate';
    } else if (newErosion <= 80) {
        color = '#b53a36'; stateName = '重度侵蚀'; bodyClass = 'severe';
    } else {
        color = '#e8e3d8'; stateName = '完全同化'; bodyClass = 'assimilated';
    }

    if (fillEl) {
        fillEl.style.width = `${newErosion}%`;
        fillEl.style.backgroundColor = color;
    }
    if (valueEl) {
        valueEl.style.color = color;
        valueEl.textContent = `${newErosion} / 100`;
    }
    if (stateEl) {
        stateEl.style.color = color;
        stateEl.textContent = stateName;
    }

    const sceneClass = Array.from(document.body.classList).find(cls => cls.startsWith('scene-'));
    document.body.className = ['game-body', bodyClass, sceneClass].filter(Boolean).join(' ');
    document.body.dataset.erosion = newErosion;
}

function appendConsequence(text) {
    const textArea = document.getElementById('textArea');
    const consequenceDiv = document.createElement('div');
    consequenceDiv.className = 'consequence-text paper-block fresh';
    consequenceDiv.innerHTML = linesToParagraphs(text);
    textArea.appendChild(consequenceDiv);
    consequenceDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function showToast(message) {
    const toast = document.getElementById('fragmentToast');
    const toastText = document.getElementById('toastText');
    toastText.textContent = message;
    toast.style.display = 'flex';
    toast.style.animation = 'none';
    toast.offsetHeight;
    toast.style.animation = 'slideIn 0.3s ease, fadeOut 0.5s ease 1.8s forwards';
    setTimeout(() => { toast.style.display = 'none'; }, 2600);
}

function showFragmentToast(fragmentIds, total) {
    showToast(`获得信息碎片：${total}/18`);
}

function showNoCostOption(desc, option) {
    const textArea = document.getElementById('textArea');
    const noCostDiv = document.createElement('div');
    noCostDiv.className = 'no-cost-option paper-block fresh';
    noCostDiv.id = 'noCostOption';
    noCostDiv.innerHTML = `
        <p class="no-cost-desc">${escapeHtml(desc)}</p>
        <button class="choice-btn no-cost-btn" onclick="openRitualModal()">
            <span>${escapeHtml(option)}</span>
            <small>侵蚀度 -3</small>
        </button>`;
    textArea.appendChild(noCostDiv);
    noCostDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function manualSave() {
    fetch('/save_manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot: 0 })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'ok') showToast('存档成功。记录已封存。');
    });
}

document.addEventListener('keydown', function(e) {
    if (e.key >= '1' && e.key <= '9') {
        const choiceIndex = parseInt(e.key, 10) - 1;
        const choiceBtn = document.querySelector(`.choice-btn[data-index="${choiceIndex}"]`);
        if (choiceBtn && !choiceBtn.disabled) makeChoice(choiceIndex);
    }
    if ((e.key === 'r' || e.key === 'R') && !e.ctrlKey && !e.metaKey && !e.altKey) viewRules();
    if ((e.key === 'n' || e.key === 'N') && !e.ctrlKey && !e.metaKey && !e.altKey) viewNotes();
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay').forEach(m => {
            if (m.id !== 'deathModal') m.style.display = 'none';
        });
    }
});

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay && overlay.id !== 'deathModal') {
                overlay.style.display = 'none';
                if (overlay.id === 'rulesModal') {
                    fetch('/choose', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ type: 'close_rules' })
                    });
                }
            }
        });
    });
});
