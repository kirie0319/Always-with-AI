// DOM要素の取得
document.addEventListener('DOMContentLoaded', () => {
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

  // CIF入力フィールド
  const cifInput = document.getElementById('cif');

  // 現在のステップを管理するための変数
  let currentStep = 0;

  // ステップの表示/非表示を更新する関数
  function updateStepVisibility() {
    // すべてのステップを非表示
    [step0, step1, step2, step3].forEach(step => {
      if (step) {
        step.classList.add('hidden');
      }
    });

    // 現在のステップを表示
    switch (currentStep) {
      case 0:
        if (step0) step0.classList.remove('hidden');
        break;
      case 1:
        if (step1) step1.classList.remove('hidden');
        break;
      case 2:
        if (step2) step2.classList.remove('hidden');
        break;
      case 3:
        if (step3) step3.classList.remove('hidden');
        break;
    }
  }

  // フォームデータを収集する関数
  function collectFormData() {
    const formData = {
      personalInfo: {
        age: parseInt(document.getElementById('age')?.value) || 0,
        industry: document.getElementById('industry')?.value || '',
        company: document.getElementById('company')?.value || '',
        position: document.getElementById('position')?.value || '',
        jobType: document.getElementById('job-type')?.value || '',
        annualIncome: parseInt(document.getElementById('annual-income')?.value) || 0,
        familyStructure: '',
        familyMembers: []
      },
      financialInfo: {
        savings: parseInt(document.getElementById('savings')?.value) || 0,
        hasInvestments: false,
        investments: [],
        retirement: parseInt(document.getElementById('retirement')?.value.replace(/,/g, '')) || 0,
        hasCar: false,
        hasHome: false,
        livingExpenses: parseInt(document.getElementById('living-expenses')?.value) || 0,
        loans: []
      },
      intentions: {
        carPurchase: false,
        homeRenovation: false,
        domesticTravel: false,
        overseasTravel: false,
        petOwnership: false,
        caregivingConcerns: false,
        otherExpenses: false,
        investmentStance: document.getElementById('investment-stance')?.value || '',
        hasChildren: false,
        childEducation: null
      }
    };

    // 家族構成の取得
    const rows = document.querySelectorAll('.financial-input-row');
    rows.forEach(row => {
      const label = row.querySelector('label');
      if (label && label.textContent.includes('家族構成')) {
        const activeButton = row.querySelector('.financial-option-button.active');
        if (activeButton) {
          formData.personalInfo.familyStructure = activeButton.dataset.value || '';
        }
      }
    });

    // 家族メンバー情報を収集
    const familyMembers = document.querySelectorAll('.family-member');
    familyMembers.forEach(member => {
      const relationSelect = member.querySelector('.family-relation');
      const ageInput = member.querySelector('.family-age');
      const occupationSelect = member.querySelector('.family-occupation');
      
      if (relationSelect && ageInput && occupationSelect) {
        formData.personalInfo.familyMembers.push({
          relation: relationSelect.value || '',
          age: parseInt(ageInput.value) || 0,
          occupation: occupationSelect.value || ''
        });
      }
    });

    // 運用資産の有無を取得
    rows.forEach(row => {
      const label = row.querySelector('label');
      if (label && label.textContent.includes('運用資産')) {
        const activeButton = row.querySelector('.financial-option-button.active');
        if (activeButton) {
          formData.financialInfo.hasInvestments = activeButton.dataset.value === 'true';
        }
      }
    });

    // 投資情報を収集
    const investments = document.querySelectorAll('.investment-item');
    investments.forEach(investment => {
      const typeSelect = investment.querySelector('.investment-type');
      const amountInput = investment.querySelector('.investment-amount');
      const nameInput = investment.querySelector('.investment-name');
      const riskSelect = investment.querySelector('.investment-risk');
      const activeMaturityButton = investment.querySelector('.financial-option-button.active');
      
      if (typeSelect && amountInput) {
        formData.financialInfo.investments.push({
          type: typeSelect.value || '',
          amount: parseInt(amountInput.value) || 0,
          name: nameInput ? nameInput.value : '',
          risk: riskSelect ? riskSelect.value : '',
          hasMaturity: activeMaturityButton ? (activeMaturityButton.dataset.value === 'true') : false
        });
      }
    });

    // 自家用車と住宅の有無を取得
    rows.forEach(row => {
      const label = row.querySelector('label');
      if (label) {
        const activeButton = row.querySelector('.financial-option-button.active');
        if (activeButton) {
          if (label.textContent.includes('自家用車')) {
            formData.financialInfo.hasCar = activeButton.dataset.value === 'true';
          } else if (label.textContent.includes('マイホーム')) {
            formData.financialInfo.hasHome = activeButton.dataset.value === 'true';
          }
        }
      }
    });

    // ローン情報を収集
    const loans = document.querySelectorAll('.loan-item');
    loans.forEach(loan => {
      const typeSelect = loan.querySelector('.loan-type');
      const balanceInput = loan.querySelector('.loan-balance');
      const monthsInput = loan.querySelector('.loan-remaining-months');
      
      if (typeSelect && balanceInput && monthsInput) {
        formData.financialInfo.loans.push({
          type: typeSelect.value || '',
          balance: parseInt(balanceInput.value.replace(/,/g, '')) || 0,
          remainingMonths: parseInt(monthsInput.value) || 0
        });
      }
    });

    // 各種ライフイベントの有無を取得
    const eventTypes = [
      { key: 'carPurchase', label: '車の購入' },
      { key: 'homeRenovation', label: '家のリフォーム' },
      { key: 'domesticTravel', label: '国内旅行' },
      { key: 'overseasTravel', label: '海外旅行' },
      { key: 'petOwnership', label: 'ペットの飼育' },
      { key: 'caregivingConcerns', label: '介護の不安' },
      { key: 'otherExpenses', label: 'その他支出' }
    ];
    
    eventTypes.forEach(event => {
      rows.forEach(row => {
        const label = row.querySelector('label');
        if (label && label.textContent.includes(event.label)) {
          const activeButton = row.querySelector('.financial-option-button.active');
          if (activeButton) {
            formData.intentions[event.key] = activeButton.dataset.value === 'true';
          }
        }
      });
    });

    // 子どもの有無を取得
    rows.forEach(row => {
      const label = row.querySelector('label');
      if (label && label.textContent.includes('お子様のご予定')) {
        const activeButton = row.querySelector('.financial-option-button.active');
        if (activeButton) {
          formData.intentions.hasChildren = activeButton.dataset.value === 'true';
        }
      }
    });

    // 子供の教育情報を収集
    if (formData.intentions.hasChildren) {
      const educationContainer = document.getElementById('child-education-container');
      if (educationContainer) {
        formData.intentions.childEducation = {
          kindergarten: '',
          elementarySchool: '',
          juniorHighSchool: '',
          highSchool: '',
          university: ''
        };
        
        const educationTypes = [
          { key: 'kindergarten', label: '幼稚園' },
          { key: 'elementarySchool', label: '小学校' },
          { key: 'juniorHighSchool', label: '中学校' },
          { key: 'highSchool', label: '高校' },
          { key: 'university', label: '大学' }
        ];
        
        educationTypes.forEach(edu => {
          const eduRows = educationContainer.querySelectorAll('.financial-input-row');
          eduRows.forEach(row => {
            const label = row.querySelector('label');
            if (label && label.textContent.includes(edu.label)) {
              const activeButton = row.querySelector('.financial-option-button.active');
              if (activeButton) {
                formData.intentions.childEducation[edu.key] = activeButton.dataset.value || '';
              }
            }
          });
        });
      }
    }

    return formData;
  }

  // CRMデータをフォームに設定する関数
  function populateFormWithCRMData(data) {
    // 実装はコードが長いため省略（実際の実装では提供されたデータをフォームに設定する）
    console.log('CRMデータをフォームに設定:', data);
    // ここに実装を追加
  }

  // イベントリスナーの設定

  // 情報連携ボタン (Step 0 -> Step 1)
  if (connectInfoBtn) {
    connectInfoBtn.addEventListener('click', async () => {
      console.log('Connect Info Button Clicked');
      if (!cifInput) {
        console.error('CIF入力フィールドが見つかりません');
        return;
      }
      
      const cifId = cifInput.value.trim();
      
      if (!cifId) {
        alert('CIF番号を入力してください');
        return;
      }
      
      try {
        // サーバーからCRMデータを取得
        const response = await fetch(`/financial/crm-data/${cifId}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        });
        
        const result = await response.json();
        
        if (!response.ok || !result.success) {
          throw new Error(result.message || 'CRMデータの取得に失敗しました');
        }
        
        console.log(`CIF ID ${cifId} のデータを取得しました:`, result.data);
        
        // フォームにデータを設定
        populateFormWithCRMData(result.data);
        
        // ステップを進める
        currentStep = 1;
        updateStepVisibility();
      } catch (error) {
        console.error('CRMデータ取得エラー:', error);
        alert(`CIF ID ${cifId} のデータの取得に失敗しました: ${error.message}`);
      }
    });
  }

  // 前へボタン (Step 1 -> Step 0)
  if (backToStep0Btn) {
    backToStep0Btn.addEventListener('click', () => {
      currentStep = 0;
      updateStepVisibility();
    });
  }

  // 次へボタン (Step 1 -> Step 2)
  if (nextToStep2Btn) {
    nextToStep2Btn.addEventListener('click', () => {
      currentStep = 2;
      updateStepVisibility();
    });
  }

  // 前へボタン (Step 2 -> Step 1)
  if (backToStep1Btn) {
    backToStep1Btn.addEventListener('click', () => {
      currentStep = 1;
      updateStepVisibility();
    });
  }

  // 次へボタン (Step 2 -> Step 3)
  if (nextToStep3Btn) {
    nextToStep3Btn.addEventListener('click', () => {
      currentStep = 3;
      updateStepVisibility();
    });
  }

  // 前へボタン (Step 3 -> Step 2)
  if (backToStep2Btn) {
    backToStep2Btn.addEventListener('click', () => {
      currentStep = 2;
      updateStepVisibility();
    });
  }

  // 完了ボタン
  if (completeFormBtn) {
    completeFormBtn.addEventListener('click', async () => {
      try {
        // フォームデータの収集
        const formData = collectFormData();
        console.log('収集したフォームデータ:', formData);
        
        // バックエンドにデータを送信
        const response = await fetch('/financial/submit', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
          throw new Error(`サーバーエラー: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('サーバーレスポンス:', result);
        
        // 成功メッセージ
        alert('フォーム情報が送信されました！');
        
        // AIアシスタントに表示するメッセージを送信
        if (typeof appendMessage === 'function') {
          appendMessage('ai', `
            お客様の情報を受け付けました。以下の情報に基づいて、最適な資産運用プランをご提案いたします。
            
            • 年齢: ${formData.personalInfo.age}歳
            • 年収: ${formData.personalInfo.annualIncome}万円
            • 貯金額: ${formData.financialInfo.savings}万円
            • 運用資産: ${formData.financialInfo.hasInvestments ? 'あり' : 'なし'}
            • 投資スタンス: ${formData.intentions.investmentStance}
            
            ご質問やご相談がございましたら、お気軽にメッセージをお送りください。
          `);
        }
      } catch (error) {
        console.error('フォーム送信エラー:', error);
        alert(`エラーが発生しました: ${error.message}`);
      }
    });
  }

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

  // 投資戦略タブの切り替え
  const investmentTabButtons = document.querySelectorAll('.investment-tab-btn');
  const investmentTabContents = document.querySelectorAll('.investment-strategy-tab');
  
  investmentTabButtons.forEach(button => {
    button.addEventListener('click', () => {
      // タブボタンの切替
      investmentTabButtons.forEach(btn => btn.classList.remove('active'));
      button.classList.add('active');
      
      // タブコンテンツの切替
      const tabId = button.getAttribute('data-tab');
      investmentTabContents.forEach(content => {
        content.classList.remove('active');
      });
      document.getElementById(tabId).classList.add('active');
    });
  });

  // 顧客情報に戻るボタン
  returnButtons.forEach(button => {
    button.addEventListener('click', () => {
      changeTab(0);
    });
  });

  // 初期表示時のステップを設定
  updateStepVisibility();
});

// タブ切り替え関数
function changeTab(index) {
  // すべてのタブからactiveクラスを削除
  const tabs = document.querySelectorAll('.financial-tab-item');
  tabs.forEach(tab => {
    tab.classList.remove('active');
  });

  // クリックされたタブにactiveクラスを追加
  if (tabs[index]) {
    tabs[index].classList.add('active');
  }
  
  // タブコンテンツの表示を切り替える
  const tabContents = document.querySelectorAll('.tab-content');
  tabContents.forEach(content => {
    content.classList.add('hidden');
    content.classList.remove('active');
  });
  
  if (index === 0) {
    const customerInfoContent = document.getElementById('customer-info-content');
    if (customerInfoContent) {
      customerInfoContent.classList.remove('hidden');
      customerInfoContent.classList.add('active');
    }
  } else if (index === 1) {
    const lifeSimulationContent = document.getElementById('life-simulation-content');
    if (lifeSimulationContent) {
      lifeSimulationContent.classList.remove('hidden');
      lifeSimulationContent.classList.add('active');
    }
  } else if (index === 2) {
    const investmentStrategyContent = document.getElementById('investment-strategy-content');
    if (investmentStrategyContent) {
      investmentStrategyContent.classList.remove('hidden');
      investmentStrategyContent.classList.add('active');
    }
  }
}