document.addEventListener('DOMContentLoaded', function () {
  // モーダル要素
  const modal = document.getElementById('preview-modal');
  const promptContent = document.getElementById('prompt-content');

  // モーダルを閉じるボタン
  const closeBtn = document.querySelector('.close-btn');
  if (closeBtn) {
    closeBtn.addEventListener('click', function () {
      modal.classList.remove('active');
    });
  }

  // モーダル外クリックで閉じる
  window.addEventListener('click', function (event) {
    if (event.target === modal) {
      modal.classList.remove('active');
    }
  });

  // プレビューボタンのイベント
  const previewButtons = document.querySelectorAll('.preview-btn');
  let currentPromptId = null; // 現在表示中のプロンプトID

  previewButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      const promptId = this.getAttribute('data-id');
      currentPromptId = promptId;
      fetchPromptContent(promptId);
    });
  });

  // 選択ボタンのイベント
  const selectButtons = document.querySelectorAll('.select-btn');
  selectButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      const promptId = this.getAttribute('data-id');
      selectPrompt(promptId);
    });
  });

  // プレビューから選択するボタン
  const selectFromPreviewBtn = document.querySelector('.select-from-preview-btn');
  if (selectFromPreviewBtn) {
    selectFromPreviewBtn.addEventListener('click', function () {
      if (currentPromptId) {
        selectPrompt(currentPromptId);
      }
    });
  }

  // プロンプト内容を取得して表示する関数
  async function fetchPromptContent(promptId) {
    try {
      const response = await fetch(`/api/prompt/${promptId}`);

      if (!response.ok) {
        throw new Error('プロンプトの取得に失敗しました');
      }

      const data = await response.json();
      promptContent.textContent = data.content;

      // モーダルを表示
      modal.classList.add('active');

    } catch (error) {
      console.error('エラー:', error);
      alert('プロンプトの取得中にエラーが発生しました');
    }
  }

  // プロンプトを選択する関数
  async function selectPrompt(promptId) {
    try {
      const response = await fetch('/api/select-prompt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin',
        body: JSON.stringify({ prompt_id: promptId })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'プロンプトの選択に失敗しました');
      }

      const data = await response.json();

      if (data.success) {
        // セッションストレージに選択したプロンプトIDを保存
        sessionStorage.setItem('selectedPromptId', promptId);
        sessionStorage.setItem('selectedPromptName', data.prompt_name);

        // 選択成功
        alert(`プロンプト「${data.prompt_name}」を選択しました`);

        // チャット画面にリダイレクト
        window.location.href = '/';
      } else {
        alert('プロンプトの選択に失敗しました: ' + data.message);
      }

    } catch (error) {
      console.error('エラー:', error);
      alert(`エラーが発生しました: ${error.message}`);
    }
  }

  // 選択されているプロンプトにハイライトを付ける
  function highlightSelectedPrompt() {
    // セッションストレージから選択済みプロンプトIDを取得
    const selectedPromptId = sessionStorage.getItem('selectedPromptId');

    if (selectedPromptId) {
      const cards = document.querySelectorAll('.prompt-card');
      cards.forEach(card => {
        const cardId = card.getAttribute('data-id');
        if (cardId === selectedPromptId) {
          card.classList.add('selected');

          // 選択ボタンのテキストを変更
          const selectBtn = card.querySelector('.select-btn');
          if (selectBtn) {
            selectBtn.innerHTML = '<i class="fas fa-check"></i> 選択中';
            selectBtn.classList.add('selected');
          }
        }
      });
    }
  }

  // ページ読み込み時に選択済みプロンプトをハイライト
  highlightSelectedPrompt();
});