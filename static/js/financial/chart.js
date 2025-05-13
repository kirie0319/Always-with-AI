// 3) Chart.js 生成
function initFinancialChart(){
    const ctx = document.getElementById('financial-combined-chart');
    if(!ctx) return;
  
    if(window.financialLifeplanChart instanceof Chart){
      window.financialLifeplanChart.destroy();
    }
  
    window.financialLifeplanChart = new Chart(ctx,{
      type:'bar',
      data:{ /* … */ },
      options:{
        responsive:true,
        maintainAspectRatio:false,   // ここ重要
        /* scales / plugins … */
      }
    });
  
    // 4) wrapper size 監視
    const wrapper = document.getElementById('financial-chart-wrapper');
    if(!wrapper.__observer){
      wrapper.__observer = new ResizeObserver(()=>{
        window.financialLifeplanChart.resize();
      }).observe(wrapper);
    }
  }
  