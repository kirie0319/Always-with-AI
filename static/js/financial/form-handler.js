/**
 * フォーム処理関連の関数
 * フォームデータの収集と操作を担当
 */

/**
 * フォームデータを収集する関数
 * @returns {Object} - 収集したフォームデータ
 */
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

/**
 * CRMデータをフォームに設定する関数
 * @param {Object} data - CRMデータ
 */
function populateFormWithCRMData(data) {
  if (!data) return;

  // 個人情報を入力
  const personalInfo = data.personalInfo;
  if (personalInfo) {
    const ageInput = document.getElementById('age');
    if (ageInput) ageInput.value = personalInfo.age || '';
    
    const industrySelect = document.getElementById('industry');
    if (industrySelect) {
      Array.from(industrySelect.options).forEach(option => {
        if (option.value === personalInfo.industry) {
          option.selected = true;
        }
      });
    }
    
    const companyInput = document.getElementById('company');
    if (companyInput) companyInput.value = personalInfo.company || '';
    
    const positionSelect = document.getElementById('position');
    if (positionSelect) {
      Array.from(positionSelect.options).forEach(option => {
        if (option.value === personalInfo.position) {
          option.selected = true;
        }
      });
    }
    
    const jobTypeSelect = document.getElementById('job-type');
    if (jobTypeSelect) {
      Array.from(jobTypeSelect.options).forEach(option => {
        if (option.value === personalInfo.jobType) {
          option.selected = true;
        }
      });
    }
    
    const annualIncomeInput = document.getElementById('annual-income');
    if (annualIncomeInput) annualIncomeInput.value = personalInfo.annualIncome || '';
    
    // 家族構成ボタン - 標準的なDOMセレクション方法を使用
    const familyStructureRows = document.querySelectorAll('.financial-input-row');
    familyStructureRows.forEach(row => {
      const label = row.querySelector('label');
      if (label && label.textContent.includes('家族構成')) {
        const buttons = row.querySelectorAll('.financial-option-button');
        buttons.forEach(button => {
          if (button.dataset.value === personalInfo.familyStructure) {
            buttons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
          }
        });
      }
    });
    
    // 家族メンバー情報
    const familyInfo = document.getElementById('family-info');
    if (familyInfo && personalInfo.familyMembers && personalInfo.familyMembers.length > 0) {
      // 既存の家族メンバー要素を全て削除 (最初の要素以外)
      const existingMembers = familyInfo.querySelectorAll('.family-member');
      for (let i = 1; i < existingMembers.length; i++) {
        existingMembers[i].remove();
      }
      
      // 最初のメンバー情報を設定
      const firstMember = existingMembers[0];
      if (firstMember && personalInfo.familyMembers[0]) {
        const relationSelect = firstMember.querySelector('.family-relation');
        if (relationSelect) {
          Array.from(relationSelect.options).forEach(option => {
            if (option.value === personalInfo.familyMembers[0].relation) {
              option.selected = true;
            }
          });
        }
        
        const ageInput = firstMember.querySelector('.family-age');
        if (ageInput) {
          ageInput.value = personalInfo.familyMembers[0].age || '';
        }
        
        const occupationSelect = firstMember.querySelector('.family-occupation');
        if (occupationSelect) {
          Array.from(occupationSelect.options).forEach(option => {
            if (option.value === personalInfo.familyMembers[0].occupation) {
              option.selected = true;
            }
          });
        }
      }
      
      // 2人目以降の家族メンバーを追加
      for (let i = 1; i < personalInfo.familyMembers.length; i++) {
        const member = personalInfo.familyMembers[i];
        const newMember = document.createElement('div');
        newMember.className = 'family-member';
        newMember.innerHTML = `
          <div class="financial-input-row">
            <label class="financial-input-row-label">続柄</label>
            <select class="family-relation">
              <option value="配偶者" ${member.relation === '配偶者' ? 'selected' : ''}>配偶者</option>
              <option value="子供" ${member.relation === '子供' ? 'selected' : ''}>子供</option>
              <option value="親" ${member.relation === '親' ? 'selected' : ''}>親</option>
              <option value="その他" ${member.relation === 'その他' ? 'selected' : ''}>その他</option>
            </select>
          </div>
          
          <div class="financial-input-row">
            <label class="financial-input-row-label">年齢</label>
            <input type="number" class="family-age" value="${member.age || ''}">
            <span>歳</span>
          </div>
          
          <div class="financial-input-row">
            <label class="financial-input-row-label">職業</label>
            <select class="family-occupation">
              <option value="会社員" ${member.occupation === '会社員' ? 'selected' : ''}>会社員</option>
              <option value="自営業" ${member.occupation === '自営業' ? 'selected' : ''}>自営業</option>
              <option value="学生" ${member.occupation === '学生' ? 'selected' : ''}>学生</option>
              <option value="無職" ${member.occupation === '無職' ? 'selected' : ''}>無職</option>
              <option value="その他" ${member.occupation === 'その他' ? 'selected' : ''}>その他</option>
            </select>
          </div>
        `;
        
        // 安全に家族メンバーを追加
        const addButton = document.getElementById('add-family-member');
        if (addButton && familyInfo.contains(addButton)) {
          // 追加ボタンの前に挿入できる場合
          familyInfo.insertBefore(newMember, addButton);
        } else {
          // ボタンがない場合や、別の親要素にある場合は末尾に追加
          familyInfo.appendChild(newMember);
        }
      }
    }
  }
  
  // 財務情報を入力
  const financialInfo = data.financialInfo;
  if (financialInfo) {
    const savingsInput = document.getElementById('savings');
    if (savingsInput) savingsInput.value = financialInfo.savings || '';
    
    // 運用資産ボタン
    const allRows = document.querySelectorAll('.financial-input-row');
    allRows.forEach(row => {
      const label = row.querySelector('label');
      if (label && label.textContent.includes('運用資産')) {
        const buttons = row.querySelectorAll('.financial-option-button');
        buttons.forEach(button => {
          if ((button.dataset.value === 'true' && financialInfo.hasInvestments) || 
              (button.dataset.value === 'false' && !financialInfo.hasInvestments)) {
            // まず全てのボタンから active クラスを削除
            buttons.forEach(btn => btn.classList.remove('active'));
            // 該当するボタンに active クラスを追加
            button.classList.add('active');
          }
        });
      }
    });
    
    // 投資情報
    const investmentsContainer = document.getElementById('investments-container');
    if (investmentsContainer && financialInfo.investments && financialInfo.investments.length > 0) {
      // 既存の投資アイテムを全て削除 (最初の要素以外)
      const existingInvestments = investmentsContainer.querySelectorAll('.investment-item');
      for (let i = 1; i < existingInvestments.length; i++) {
        existingInvestments[i].remove();
      }
      
      // 最初の投資情報を設定
      const firstInvestment = existingInvestments[0];
      if (firstInvestment && financialInfo.investments[0]) {
        const typeSelect = firstInvestment.querySelector('.investment-type');
        if (typeSelect) {
          Array.from(typeSelect.options).forEach(option => {
            if (option.value === financialInfo.investments[0].type) {
              option.selected = true;
            }
          });
        }
        
        const amountInput = firstInvestment.querySelector('.investment-amount');
        if (amountInput) {
          amountInput.value = financialInfo.investments[0].amount || '';
        }
        
        const nameInput = firstInvestment.querySelector('.investment-name');
        if (nameInput) {
          nameInput.value = financialInfo.investments[0].name || '';
        }
        
        const riskSelect = firstInvestment.querySelector('.investment-risk');
        if (riskSelect) {
          Array.from(riskSelect.options).forEach(option => {
            if (option.value === financialInfo.investments[0].risk) {
              option.selected = true;
            }
          });
        }
        
        // 満期ボタン
        const maturityButtons = firstInvestment.querySelectorAll('.financial-option-button');
        maturityButtons.forEach(button => {
          if ((button.dataset.value === 'true' && financialInfo.investments[0].hasMaturity) || 
              (button.dataset.value === 'false' && !financialInfo.investments[0].hasMaturity)) {
            // まず全てのボタンから active クラスを削除
            const parentGroup = button.closest('.financial-button-group');
            if (parentGroup) {
              parentGroup.querySelectorAll('.financial-option-button').forEach(btn => {
                btn.classList.remove('active');
              });
            }
            // 該当するボタンに active クラスを追加
            button.classList.add('active');
          }
        });
      }
      
      // 2つ目以降の投資情報を追加
      for (let i = 1; i < financialInfo.investments.length; i++) {
        const investment = financialInfo.investments[i];
        const newInvestment = document.createElement('div');
        newInvestment.className = 'investment-item';
        newInvestment.innerHTML = `
          <div class="financial-input-row">
            <label class="financial-input-row-label">金融商品</label>
            <select class="investment-type">
              <option value="投資信託" ${investment.type === '投資信託' ? 'selected' : ''}>投資信託</option>
              <option value="株式" ${investment.type === '株式' ? 'selected' : ''}>株式</option>
              <option value="債券" ${investment.type === '債券' ? 'selected' : ''}>債券</option>
              <option value="ETF" ${investment.type === 'ETF' ? 'selected' : ''}>ETF</option>
              <option value="その他" ${investment.type === 'その他' ? 'selected' : ''}>その他</option>
            </select>
          </div>
          
          <div class="financial-input-row">
            <label class="financial-input-row-label">運用金額</label>
            <input type="text" class="investment-amount" value="${investment.amount || ''}">
            <span>万円</span>
          </div>
          
          <div class="financial-input-row">
            <label class="financial-input-row-label">商品名</label>
            <input type="text" class="investment-name" value="${investment.name || ''}">
          </div>
          
          <div class="financial-input-row">
            <label class="financial-input-row-label">リスク</label>
            <select class="investment-risk">
              <option value="" ${!investment.risk ? 'selected' : ''}>リスクを選択してください</option>
              <option value="低リスク" ${investment.risk === '低リスク' ? 'selected' : ''}>低リスク</option>
              <option value="中リスク" ${investment.risk === '中リスク' ? 'selected' : ''}>中リスク</option>
              <option value="高リスク" ${investment.risk === '高リスク' ? 'selected' : ''}>高リスク</option>
            </select>
          </div>
          
          <div class="financial-input-row">
            <label class="financial-input-row-label">満期</label>
            <div class="financial-button-group">
              <button class="financial-option-button ${investment.hasMaturity ? 'active' : ''}" data-value="true">あり</button>
              <button class="financial-option-button ${!investment.hasMaturity ? 'active' : ''}" data-value="false">なし</button>
            </div>
          </div>
        `;
        
        // 安全に投資情報を追加
        const addButton = document.getElementById('add-investment');
        if (addButton && investmentsContainer.contains(addButton)) {
          // 追加ボタンの前に挿入できる場合
          investmentsContainer.insertBefore(newInvestment, addButton);
        } else {
          // ボタンがない場合や、別の親要素にある場合は末尾に追加
          investmentsContainer.appendChild(newInvestment);
        }
      }
    }
    
    const retirementInput = document.getElementById('retirement');
    if (retirementInput) retirementInput.value = financialInfo.retirement || '';
    
    // 自家用車と住宅のボタン
    const carRows = Array.from(document.querySelectorAll('.financial-input-row')).filter(row => {
      const label = row.querySelector('label');
      return label && label.textContent.includes('自家用車');
    });
    
    if (carRows.length > 0) {
      const carRow = carRows[0];
      const carButtons = carRow.querySelectorAll('.financial-option-button');
      carButtons.forEach(button => {
        if ((button.dataset.value === 'true' && financialInfo.hasCar) || 
            (button.dataset.value === 'false' && !financialInfo.hasCar)) {
          carButtons.forEach(btn => btn.classList.remove('active'));
          button.classList.add('active');
        }
      });
    }
    
    const homeRows = Array.from(document.querySelectorAll('.financial-input-row')).filter(row => {
      const label = row.querySelector('label');
      return label && label.textContent.includes('マイホーム');
    });
    
    if (homeRows.length > 0) {
      const homeRow = homeRows[0];
      const homeButtons = homeRow.querySelectorAll('.financial-option-button');
      homeButtons.forEach(button => {
        if ((button.dataset.value === 'true' && financialInfo.hasHome) || 
            (button.dataset.value === 'false' && !financialInfo.hasHome)) {
          homeButtons.forEach(btn => btn.classList.remove('active'));
          button.classList.add('active');
        }
      });
    }
    
    const livingExpensesInput = document.getElementById('living-expenses');
    if (livingExpensesInput) livingExpensesInput.value = financialInfo.livingExpenses || '';
    
    // ローン情報
    const loanItems = document.querySelectorAll('.loan-item');
    const loanContainer = loanItems.length > 0 ? loanItems[0].parentElement : null;
    
    if (loanContainer && financialInfo.loans && financialInfo.loans.length > 0) {
      // 既存のローンアイテムを全て削除 (最初の要素以外)
      for (let i = 1; i < loanItems.length; i++) {
        loanItems[i].remove();
      }
      
      // 最初のローン情報を設定
      const firstLoan = loanItems[0];
      if (firstLoan && financialInfo.loans[0]) {
        const typeSelect = firstLoan.querySelector('.loan-type');
        if (typeSelect) {
          Array.from(typeSelect.options).forEach(option => {
            if (option.value === financialInfo.loans[0].type) {
              option.selected = true;
            }
          });
        }
        
        const balanceInput = firstLoan.querySelector('.loan-balance');
        if (balanceInput) {
          balanceInput.value = financialInfo.loans[0].balance || '';
        }
        
        const monthsInput = firstLoan.querySelector('.loan-remaining-months');
        if (monthsInput) {
          monthsInput.value = financialInfo.loans[0].remainingMonths || '';
        }
      }
      
      // 2つ目以降のローン情報を追加
      for (let i = 1; i < financialInfo.loans.length; i++) {
        const loan = financialInfo.loans[i];
        const newLoan = document.createElement('div');
        newLoan.className = 'loan-item';
        newLoan.innerHTML = `
          <div class="financial-input-row">
            <label class="financial-input-row-label">種別</label>
            <select class="loan-type">
              <option value="住宅ローン" ${loan.type === '住宅ローン' ? 'selected' : ''}>住宅ローン</option>
              <option value="自動車ローン" ${loan.type === '自動車ローン' ? 'selected' : ''}>自動車ローン</option>
              <option value="教育ローン" ${loan.type === '教育ローン' ? 'selected' : ''}>教育ローン</option>
              <option value="フリーローン" ${loan.type === 'フリーローン' ? 'selected' : ''}>フリーローン</option>
              <option value="その他" ${loan.type === 'その他' ? 'selected' : ''}>その他</option>
            </select>
          </div>
          
          <div class="financial-input-row">
            <label class="financial-input-row-label">残高</label>
            <input type="text" class="loan-balance" value="${loan.balance || ''}">
            <span>万円</span>
          </div>
          
          <div class="financial-input-row">
            <label class="financial-input-row-label">残月数</label>
            <input type="text" class="loan-remaining-months" value="${loan.remainingMonths || ''}">
            <span>ヶ月</span>
          </div>
        `;
        
        // 安全にローン情報を追加
        const addButton = document.getElementById('add-loan');
        if (addButton && loanContainer.contains(addButton)) {
          // 追加ボタンの前に挿入できる場合
          loanContainer.insertBefore(newLoan, addButton);
        } else {
          // ボタンがない場合や、別の親要素にある場合は末尾に追加
          loanContainer.appendChild(newLoan);
        }
      }
    }
  }
  
  // 各種ご意向を入力
  const intentions = data.intentions;
  if (intentions) {
    // 各種ライフイベントのボタン
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
      const rows = Array.from(document.querySelectorAll('.financial-input-row')).filter(row => {
        const label = row.querySelector('label');
        return label && label.textContent.includes(event.label);
      });
      
      if (rows.length > 0) {
        const eventRow = rows[0];
        const buttons = eventRow.querySelectorAll('.financial-option-button');
        buttons.forEach(button => {
          if ((button.dataset.value === 'true' && intentions[event.key]) || 
              (button.dataset.value === 'false' && !intentions[event.key])) {
            buttons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
          }
        });
      }
    });
    
    // 投資スタンス
    const investmentStanceSelect = document.getElementById('investment-stance');
    if (investmentStanceSelect) {
      Array.from(investmentStanceSelect.options).forEach(option => {
        if (option.value === intentions.investmentStance) {
          option.selected = true;
        }
      });
    }
    
    // 子どもの有無
    const childRows = Array.from(document.querySelectorAll('.financial-input-row')).filter(row => {
      const label = row.querySelector('label');
      return label && label.textContent.includes('お子様のご予定');
    });
    
    if (childRows.length > 0) {
      const childRow = childRows[0];
      const childButtons = childRow.querySelectorAll('.financial-option-button');
      childButtons.forEach(button => {
        if ((button.dataset.value === 'true' && intentions.hasChildren) || 
            (button.dataset.value === 'false' && !intentions.hasChildren)) {
          childButtons.forEach(btn => btn.classList.remove('active'));
          button.classList.add('active');
        }
      });
    }
    
    // 子どもの教育情報
    if (intentions.childEducation) {
      const educationContainer = document.getElementById('child-education-container');
      if (educationContainer) {
        const educationTypes = [
          { key: 'kindergarten', label: '幼稚園' },
          { key: 'elementarySchool', label: '小学校' },
          { key: 'juniorHighSchool', label: '中学校' },
          { key: 'highSchool', label: '高校' },
          { key: 'university', label: '大学' }
        ];
        
        educationTypes.forEach(edu => {
          const rows = Array.from(educationContainer.querySelectorAll('.financial-input-row')).filter(row => {
            const label = row.querySelector('label');
            return label && label.textContent.includes(edu.label);
          });
          
          if (rows.length > 0) {
            const eduRow = rows[0];
            const buttons = eduRow.querySelectorAll('.financial-option-button');
            buttons.forEach(button => {
              if (button.dataset.value === intentions.childEducation[edu.key]) {
                buttons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
              }
            });
          }
        });
      }
    }
  }
}

export {
  collectFormData,
  populateFormWithCRMData
};