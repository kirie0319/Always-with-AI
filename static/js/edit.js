document.addEventListener('DOMContentLoaded', function () {
  // ID要素が存在するか確認（存在しない場合は何もしない）
  const idElement = document.getElementById('id');
  if (!idElement) return;

  const promptId = idElement.value;

  // 更新フォームの送信
  document.getElementById('edit-prompt-form').addEventListener('submit', function (e) {
    e.preventDefault();

    const formData = {
      content: document.getElementById('content').value,
      name: document.getElementById('name').value,
      description: document.getElementById('description').value
    };

    updatePrompt(promptId, formData);
  });

  // 削除ボタンのイベントリスナー
  document.getElementById('delete-btn').addEventListener('click', function () {
    deletePrompt(promptId);
  });

  // プロンプト更新関数
  async function updatePrompt(id, data) {
    try {
      const response = await fetch(`/prompt/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });

      if (response.ok) {
        alert('プロンプトが更新されました');
        // 一瞬してからリロードする（ユーザーが通知を確認できるように）
        setTimeout(() => {
          location.reload();
        }, 500);
      } else {
        alert('更新に失敗しました');
      }
    } catch (error) {
      console.error('エラー:', error);
      alert('エラーが発生しました');
    }
  }

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
        // 一覧ページにリダイレクト
        window.location.href = '/prompt';
      } else {
        alert('削除に失敗しました');
      }
    } catch (error) {
      console.error('エラー:', error);
      alert('エラーが発生しました');
    }
  }

  // テキストエリアの自動リサイズ
  const textarea = document.getElementById('content');
  if (textarea) {
    // 初期高さを設定
    adjustTextareaHeight(textarea);

    // 入力時に高さを調整
    textarea.addEventListener('input', function () {
      adjustTextareaHeight(this);
    });
  }

  // テキストエリアの高さを内容に合わせて調整する関数
  function adjustTextareaHeight(element) {
    element.style.height = 'auto';
    element.style.height = element.scrollHeight + 'px';
  }
});