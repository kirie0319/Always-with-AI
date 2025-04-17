// DOM要素の取得
document.addEventListener('DOMContentLoaded', () => {
  // タブナビゲーション
  const tabItems = document.querySelectorAll('.financial-tab-item');
  const tabContents = document.querySelectorAll('.tab-content');

  // 多段階フォーム
  const step0 = document.getElementById('step-0');
  const step1 = document.getElementById('step-1');
  const step2 = document.getElementById('step-2');
  const step3 = document.getElementById('step-3');

  // ボタン
  const connectInfoBtn = document.getElementById('connect-info-btn');
  const backToStep0Btn = document.getElementById('back-to-step-0');
  const nextToStep2Btn = document.getElementById('next-to-step-2');
  const backToStep1Btn = document.getElementById('back-to-step-1');
  const nextToStep3Btn = document.getElementById('next-to-step-3');
  const backToStep2Btn = document.getElementById('back-to-step-2');
  const completeFormBtn = document.getElementById('complete-form');
  const returnButtons = document.querySelectorAll('.return-to-customer-info');

  // オプションボタン
  const optionButtons = document.querySelectorAll('.financial-option-button');

  // タブ切り替え
  tabItems.forEach((tab) => {
    tab.addEventListener('click', () => {
      // アクティブクラスをすべてのタブから削除
      tabItems.forEach((item) => {
        item.classList.remove('active');
      });

      // クリックされたタブにアクティブクラスを追加
      tab.classList.add('active');

      // 対応するコンテンツを表示
      const tabId = tab.getAttribute('data-tab');
      tabContents.forEach((content) => {
        content.classList.remove('active');
        content.classList.add('hidden');
      });

      document.getElementById(`${tabId}-content`).classList.remove('hidden');
      document.getElementById(`${tabId}-content`).classList.add('active');

      // 顧客情報タブに戻る場合、最後に表示していたステップを表示
      if (tabId === 'customer-info') {
        updateStepVisibility();
      }
    });
  });

  // 「現在開発中」タブから顧客情報に戻るボタン
  returnButtons.forEach((button) => {
    button.addEventListener('click', () => {
      // タブ切り替え
      tabItems.forEach((item) => {
        item.classList.remove('active');
      });

      tabItems[0].classList.add('active');

      tabContents.forEach((content) => {
        content.classList.remove('active');
        content.classList.add('hidden');
      });

      document.getElementById('customer-info-content').classList.remove('hidden');
      document.getElementById('customer-info-content').classList.add('active');

      // 最後に表示していたステップを表示
      updateStepVisibility();
    });
  });

  // 現在のステップを管理するための変数
  let currentStep = 0;

  // ステップの表示/非表示を更新する関数
  function updateStepVisibility() {
    // すべてのステップを非表示
    [step0, step1, step2, step3].forEach(step => {
      step.classList.add('hidden');
    });

    // 現在のステップを表示
    switch (currentStep) {
      case 0:
        step0.classList.remove('hidden');
        break;
      case 1:
        step1.classList.remove('hidden');
        break;
      case 2:
        step2.classList.remove('hidden');
        break;
      case 3:
        step3.classList.remove('hidden');
        break;
    }
  }

  // 情報連携ボタン (Step 0 -> Step 1)
  connectInfoBtn.addEventListener('click', () => {
    currentStep = 1;
    updateStepVisibility();
  });

  // 前へボタン (Step 1 -> Step 0)
  if (backToStep0Btn) {
    backToStep0Btn.addEventListener('click', () => {
      currentStep = 0;
      updateStepVisibility();
    });
  }

  // 次へボタン (Step 1 -> Step 2)
  nextToStep2Btn.addEventListener('click', () => {
    currentStep = 2;
    updateStepVisibility();
  });

  // 前へボタン (Step 2 -> Step 1)
  backToStep1Btn.addEventListener('click', () => {
    currentStep = 1;
    updateStepVisibility();
  });

  // 次へボタン (Step 2 -> Step 3)
  nextToStep3Btn.addEventListener('click', () => {
    currentStep = 3;
    updateStepVisibility();
  });

  // 前へボタン (Step 3 -> Step 2)
  backToStep2Btn.addEventListener('click', () => {
    currentStep = 2;
    updateStepVisibility();
  });

  // 完了ボタン
  completeFormBtn.addEventListener('click', () => {
    alert('フォームが完了しました！');
    // ここに完了時の処理を追加（例：データの送信など）
  });

  // オプションボタンの選択処理
  optionButtons.forEach((button) => {
    button.addEventListener('click', () => {
      // 同じグループ内の他のボタンからアクティブクラスを削除
      const parentGroup = button.closest('.financial-button-group');
      if (parentGroup) {
        parentGroup.querySelectorAll('.financial-option-button').forEach((groupButton) => {
          groupButton.classList.remove('active');
        });
      }

      // クリックされたボタンにアクティブクラスを追加
      button.classList.add('active');
    });
  });

  // 家族メンバー追加ボタン
  const addFamilyMemberBtn = document.getElementById('add-family-member');
  if (addFamilyMemberBtn) {
    addFamilyMemberBtn.addEventListener('click', () => {
      const familyInfo = document.getElementById('family-info');
      const newMember = document.createElement('div');
      newMember.className = 'family-member';
      newMember.innerHTML = `
        <div class="financial-input-row">
          <label class="financial-input-row-label">続柄</label>
          <select class="family-relation">
            <option value="配偶者">配偶者</option>
            <option value="子供">子供</option>
            <option value="親">親</option>
            <option value="その他">その他</option>
          </select>
        </div>
        
        <div class="financial-input-row">
          <label class="financial-input-row-label">年齢</label>
          <input type="number" class="family-age" value="">
          <span>歳</span>
        </div>
        
        <div class="financial-input-row">
          <label class="financial-input-row-label">職業</label>
          <select class="family-occupation">
            <option value="会社員">会社員</option>
            <option value="自営業">自営業</option>
            <option value="学生">学生</option>
            <option value="無職">無職</option>
            <option value="その他">その他</option>
          </select>
        </div>
      `;

      // 追加ボタンの前に新しいメンバーを挿入
      familyInfo.insertBefore(newMember, addFamilyMemberBtn);
    });
  }

  // 投資商品追加ボタン
  const addInvestmentBtn = document.getElementById('add-investment');
  if (addInvestmentBtn) {
    addInvestmentBtn.addEventListener('click', () => {
      const container = document.getElementById('investments-container');
      const newInvestment = document.createElement('div');
      newInvestment.className = 'investment-item';
      newInvestment.innerHTML = `
        <div class="financial-input-row">
          <label class="financial-input-row-label">金融商品</label>
          <select class="investment-type">
            <option value="投資信託">投資信託</option>
            <option value="株式">株式</option>
            <option value="債券">債券</option>
            <option value="ETF">ETF</option>
            <option value="その他">その他</option>
          </select>
        </div>
        
        <div class="financial-input-row">
          <label class="financial-input-row-label">運用金額</label>
          <input type="text" class="investment-amount" value="">
          <span>万円</span>
        </div>
        
        <div class="financial-input-row">
          <label class="financial-input-row-label">商品名</label>
          <input type="text" class="investment-name" value="">
        </div>
        
        <div class="financial-input-row">
          <label class="financial-input-row-label">リスク</label>
          <select class="investment-risk">
            <option value="任意">任意</option>
            <option value="低リスク">低リスク</option>
            <option value="中リスク">中リスク</option>
            <option value="高リスク">高リスク</option>
          </select>
        </div>
        
        <div class="financial-input-row">
          <label class="financial-input-row-label">満期</label>
          <div class="financial-button-group">
            <button class="financial-option-button active" data-value="true">あり</button>
            <button class="financial-option-button" data-value="false">なし</button>
          </div>
        </div>
      `;

      // 追加ボタンの前に新しい投資商品を挿入
      container.insertBefore(newInvestment, addInvestmentBtn);

      // 新しく追加された項目のオプションボタンにイベントリスナーを設定
      const newButtons = newInvestment.querySelectorAll('.financial-option-button');
      newButtons.forEach((button) => {
        button.addEventListener('click', () => {
          const parentGroup = button.closest('.financial-button-group');
          if (parentGroup) {
            parentGroup.querySelectorAll('.financial-option-button').forEach((groupButton) => {
              groupButton.classList.remove('active');
            });
          }
          button.classList.add('active');
        });
      });
    });
  }

  // ローン追加ボタン
  const addLoanBtn = document.getElementById('add-loan');
  if (addLoanBtn) {
    addLoanBtn.addEventListener('click', () => {
      const container = addLoanBtn.closest('.financial-section-container');
      const newLoan = document.createElement('div');
      newLoan.className = 'loan-item';
      newLoan.innerHTML = `
        <div class="financial-input-row">
          <label class="financial-input-row-label">種別</label>
          <select class="loan-type">
            <option value="住宅ローン">住宅ローン</option>
            <option value="自動車ローン">自動車ローン</option>
            <option value="教育ローン">教育ローン</option>
            <option value="フリーローン">フリーローン</option>
            <option value="その他">その他</option>
          </select>
        </div>
        
        <div class="financial-input-row">
          <label class="financial-input-row-label">残高</label>
          <input type="text" class="loan-balance" value="">
          <span>万円</span>
        </div>
        
        <div class="financial-input-row">
          <label class="financial-input-row-label">残月数</label>
          <input type="text" class="loan-remaining-months" value="">
          <span>ヶ月</span>
        </div>
      `;

      // 追加ボタンの前に新しいローンを挿入
      container.insertBefore(newLoan, addLoanBtn);
    });
  }
});