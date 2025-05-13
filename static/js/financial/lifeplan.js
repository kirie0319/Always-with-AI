document.addEventListener('DOMContentLoaded', () => {

    // ライフプランシミュレーションタブが表示されたときのみグラフを初期化
    const initFinancialChart = () => {
        // 既存のチャートがあれば破棄する（タブ切り替え時に再描画するため）
        if (window.financialLifeplanChart instanceof Chart) {
            window.financialLifeplanChart.destroy();
        }

        // --- 統合グラフ ---
        const ctx = document.getElementById('financial-combined-chart');
        if (!ctx) return; // グラフ要素がなければ処理を中止

        // 年齢ラベル (X軸)
        const ageLabels = ['40', '45', '50', '55', '60', '65', '70', '75', '80', '85'];

        // 預金残高データ (近似値) - 棒グラフ (Y軸1)
        const depositBalanceData = [800, 1500, 2200, 2700, 2900, 2500, 1700, 1200, 800, 400];
        // 資産残高データ (近似値) - 棒グラフ (Y軸1)
        const assetBalanceData = [2000, 2800, 4000, 4800, 5200, 5000, 4500, 4000, 3800, 3500];
        // 収支バランスデータ (近似値) - 折れ線グラフ (Y軸2)
        const incomeExpenseBalanceData = [250, 250, 250, -50, -50, -250, -250, -50, -50, -50];

        window.financialLifeplanChart = new Chart(ctx, {
            type: 'bar', // 基本タイプは棒グラフ
            data: {
                labels: ageLabels,
                datasets: [
                    {
                        label: '預金残高 (万円)',
                        data: depositBalanceData,
                        backgroundColor: 'rgba(75, 192, 192, 0.6)', // 緑色系
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1,
                        yAxisID: 'y', // 左側のY軸を使用
                        order: 2 // 棒グラフを後ろに描画
                    },
                    {
                        label: '資産残高 (万円)',
                        data: assetBalanceData,
                        backgroundColor: 'rgba(54, 162, 235, 0.6)', // 青色系
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1,
                        yAxisID: 'y', // 左側のY軸を使用
                        order: 3 // 棒グラフを後ろに描画 (預金残高よりさらに後ろ)
                    },
                    {
                        label: '収支バランス (万円)',
                        data: incomeExpenseBalanceData,
                        type: 'line', // このデータセットは折れ線グラフ
                        borderColor: 'rgba(255, 159, 64, 1)', // オレンジ色系
                        backgroundColor: 'rgba(255, 159, 64, 0.2)',
                        borderWidth: 3,
                        pointRadius: 5, // 点のサイズ
                        pointHoverRadius: 7, // ホバー時の点のサイズ
                        tension: 0.1, // 線の曲がり具合
                        fill: false, // 線の下を塗りつぶさない
                        yAxisID: 'y1', // 右側のY軸を使用
                        order: 1 // 折れ線グラフを一番前に描画
                    }
                ]
            },
            options: {
                responsive: true, // レスポンシブ対応
                maintainAspectRatio: false, // アスペクト比を維持しない (コンテナに合わせる)
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '年齢'
                        }
                    },
                    y: { // 左側のY軸 (預金残高 & 資産残高)
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: '残高 (万円)' // 軸ラベルを統合
                        },
                        // Y軸の範囲を -6000 から 6000 に変更
                        suggestedMin: -6000, // 最小値を -6000 に設定
                        suggestedMax: 6000   // 最大値は 6000 のまま
                    },
                    y1: { // 右側のY軸 (収支バランス)
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: '収支バランス (万円)'
                        },
                        suggestedMin: -300, // 軸の最小値を示唆
                        suggestedMax: 300,  // 軸の最大値を示唆
                        // グリッド線を他の軸と重ならないようにする
                        grid: {
                            drawOnChartArea: false, // グリッド線をグラフエリアに描画しない
                        },
                    }
                },
                plugins: {
                    tooltip: { // ツールチップの設定
                        mode: 'index', // 同じX軸上のデータをまとめて表示
                        intersect: false, // ホバー時に点が重ならなくても表示
                    },
                    legend: { // 凡例の設定
                        position: 'bottom', // 下部に表示
                    }
                },
                interaction: { // インタラクション設定
                    mode: 'index',
                    intersect: false,
                }
            }
        });
    };

    // マイナスの値を赤色で表示するための機能追加
    const highlightNegativeValues = () => {
        // 貯蓄残高や年間現金収支のマイナス値に色付け
        document.querySelectorAll('#financial-savings-balance td, #financial-annual-cashflow td').forEach(cell => {
            if (cell.textContent.includes('-')) {
                cell.style.color = '#dc2626'; // 赤色 (red-600)
            }
        });
    };

    // タブ切り替え機能との連携（メインのJavaScriptにある場合）
    const initializeLifeplanTab = () => {
        // ライフプランシミュレーションタブを選択している場合
        if (document.querySelector('.financial-tab-item:nth-child(2).active')) {
            initFinancialChart();
            highlightNegativeValues();
        }
    };

    // ライフプランシミュレーションタブが表示された際の処理
    if (typeof changeTab === 'function') {
        // メインJSのchangeTab関数がある場合の処理
        const originalChangeTab = changeTab;
        
        // 関数をオーバーライド
        window.changeTab = (tabIndex) => {
            originalChangeTab(tabIndex);
            
            // ライフプランシミュレーションタブの場合
            if (tabIndex === 1) {
                initFinancialChart();
                highlightNegativeValues();
            }
        };
    } else {
        // 単体テスト用 - ライフプランシミュレーションページのみの場合
        initFinancialChart();
        highlightNegativeValues();
    }

    // ウィンドウリサイズ時のグラフ再描画
    window.addEventListener('resize', () => {
        if (document.getElementById('financial-combined-chart')) {
            // 0.3秒のデバウンス処理
            if (window.resizeTimeout) {
                clearTimeout(window.resizeTimeout);
            }
            window.resizeTimeout = setTimeout(() => {
                if (window.financialLifeplanChart instanceof Chart) {
                    window.financialLifeplanChart.resize();
                }
            }, 300);
        }
    });

    // データテーブルのセル内表示改善
    const formatFinancialTable = () => {
        // 金額表示のあるセルにカンマを追加（未実装の場合）
        document.querySelectorAll('.financial-data-cell').forEach(cell => {
            const content = cell.textContent.trim();
            if (/^-?\d+,?\d*$/.test(content.replace(/,/g, '')) && content !== '') {
                // すでにカンマが含まれていない数値のみ処理
                if (!content.includes(',')) {
                    const num = parseInt(content.replace(/,/g, ''));
                    if (!isNaN(num)) {
                        cell.textContent = num.toLocaleString();
                    }
                }
            }
        });
    };

    // 初期ロード時に表の金額表示を整形
    formatFinancialTable();

    // イベントリスナーをページ読み込み時に一度だけ実行
    initializeLifeplanTab();
});