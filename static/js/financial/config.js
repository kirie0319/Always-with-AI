/**
 * Financial Supporter AIの設定
 * アプリケーション全体で使用される設定値を定義
 */
const config = {
    // API関連
    apiBaseUrl: '',
    endpoints: {
      crmData: '/financial/crm-data/',
      formSubmit: '/financial/submit',
      conversationHistory: '/conversation_history',
      chat: '/chat',
      langchainChat: '/langchain_chat',
      validateToken: '/validate-token',
      clear: '/clear'
    },
  
    // UI関連
    defaultStep: 0,
    
    // ローカルストレージキー
    storageKeys: {
      accessToken: 'access_token',
      selectedPromptName: 'selectedPromptName'
    }
  };
  
  export default config;