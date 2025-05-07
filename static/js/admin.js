document.addEventListener('DOMContentLoaded', () => {
    const promptCards = document.querySelectorAll('.prompt-card');
    const projectSection = document.querySelector('.project-selection');
    const projectCards = document.querySelectorAll('.project-card');

    // Prompt selection logic
    promptCards.forEach(card => {
        card.querySelector('.select-prompt-btn').addEventListener('click', () => {
            // Remove active state from all prompt cards
            promptCards.forEach(c => c.classList.remove('active'));
            
            // Add active state to selected card
            card.classList.add('active');
            
            // Show project selection section
            projectSection.style.display = 'block';
        });
    });

    // Project selection logic
    projectCards.forEach(card => {
        card.querySelector('.select-project-btn').addEventListener('click', () => {
            const promptId = document.querySelector('.prompt-card.active').dataset.promptId;
            const projectId = card.dataset.projectId;

            // Send selected prompt and project to server
            fetch('/select_project', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt_id: promptId,
                    project_id: projectId
                })
            })
            .then(response => response.json())
            .then(data => {
                // Redirect to the selected project page
                window.location.href = data.redirect_url;
            })
            .catch(error => {
                console.error('Error:', error);
                alert('プロジェクトの選択中にエラーが発生しました。');
            });
        });
    });
});
