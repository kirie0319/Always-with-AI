document.addEventListener('DOMContentLoaded', function () {
  // 削除ボタンのイベントリスナー
  document.querySelectorAll('.delete-btn').forEach(button => {
    button.addEventListener('click', function () {
      const promptId = this.getAttribute('data-id');
      deletePrompt(promptId);
    });
  });

  // プロンプト作成フォームの送信
  document.getElementById('create-prompt-form').addEventListener('submit', function (e) {
    e.preventDefault();

    const formData = {
      name: document.getElementById('name').value,
      description: document.getElementById('description').value,
      content: document.getElementById('content').value
    };

    createPrompt(formData);
  });

  // プロンプト削除関数
  async function deletePrompt(id) {
    if (!confirm('本当にこのプロンプトを削除しますか？')) return;

    try {
      const response = await fetch(`/prompt/${id}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        alert('プロンプトが削除されました');
        location.reload();
      } else {
        alert('削除に失敗しました');
      }
    } catch (error) {
      console.error('エラー:', error);
      alert('エラーが発生しました');
    }
  }

  // プロンプト作成関数
  async function createPrompt(data) {
    try {
      const response = await fetch('/prompts/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });

      if (response.ok) {
        alert('プロンプトが作成されました');
        location.reload();
      } else {
        alert('作成に失敗しました');
      }
    } catch (error) {
      console.error('エラー:', error);
      alert('エラーが発生しました');
    }
  }
});