/**
 * Main application logic
 */

const app = {
    password: null,
    token: null,
    data: {
        daily: {},
        weight: {},
        products: []
    },
    today: new Date().toISOString().split('T')[0],
    config: {
        calorie_target: 1800,
        protein_target_g: 130,
        water_target_l: 2.0,
        calorie_zones: { green_max: 1900, yellow_max: 2200 }
    },
    meals: ['завтрак', '2-й завтрак', 'обед', 'полдник', 'ужин', 'поздний перекус'],
    drinks: [
        'Кофе молотый с молоком 200мл',
        'Латте 300мл',
        'Чай чёрный 200мл',
        'Чай зелёный 200мл',
        'Чай с вареньем 200мл',
        'Вода стакан 200мл',
        'Вода с газом литры'
    ],

    async authenticate() {
        const pwd = document.getElementById('passwordInput').value;
        if (!pwd) {
            this.showError('Введите пароль');
            return;
        }

        try {
            this.password = pwd;

            // Hide password screen, show dashboard
            const screenEl = document.getElementById('passwordScreen');
            const dashboardEl = document.getElementById('dashboard');
            if (screenEl) screenEl.style.display = 'none';
            if (dashboardEl) dashboardEl.classList.add('visible');

            // Set today's date if elements exist
            const entryDateEl = document.getElementById('entryDate');
            const weightDateEl = document.getElementById('weightDate');
            if (entryDateEl) entryDateEl.valueAsDate = new Date();
            if (weightDateEl) weightDateEl.valueAsDate = new Date();

            // Load token if exists
            try {
                await this.loadToken();
            } catch (e) {
                console.warn('Token load failed:', e);
            }

            // Initialize forms
            try {
                this.initializeMealForms();
                this.initializeDrinksForms();
            } catch (e) {
                console.warn('Form init failed:', e);
            }

            // Set theme from localStorage
            const theme = localStorage.getItem('theme') || 'dark';
            this.setTheme(theme);

            console.log('✓ Authenticated successfully');
        } catch (err) {
            this.showError('Ошибка аутентификации: ' + (err?.message || err));
            console.error(err);
        }
    },

    async loadToken() {
        const encrypted = localStorage.getItem('github_token_encrypted');
        if (encrypted) {
            try {
                this.token = await API.decryptToken(this.password);
                document.getElementById('tokenStatus').textContent = '✓ Токен сохранён';
            } catch {
                document.getElementById('tokenStatus').textContent = '⚠ Токен не доступен (может быть разблокирован пароль)';
            }
        } else {
            document.getElementById('tokenStatus').textContent = '—';
        }
    },

    initializeMealForms() {
        const container = document.getElementById('mealsContainer');
        container.innerHTML = '';

        this.meals.forEach(meal => {
            const section = document.createElement('div');
            section.className = 'meal-section';
            section.innerHTML = `
                <h3>${meal.charAt(0).toUpperCase() + meal.slice(1)}</h3>
                <div class="meal-items" id="meal-${meal}"></div>
                <button class="btn btn-add" onclick="app.addMealItem('${meal}')">+ Добавить продукт</button>
            `;
            container.appendChild(section);
        });
    },

    initializeDrinksForms() {
        const grid = document.getElementById('drinksGrid');
        grid.innerHTML = '';

        this.drinks.forEach(drink => {
            const card = document.createElement('div');
            card.className = 'drink-card';
            card.innerHTML = `
                <div class="drink-name">${drink}</div>
                <div class="drink-counter">
                    <button class="drink-btn" onclick="app.updateDrink('${drink}', -1)">−</button>
                    <span style="width: 40px; text-align: center;" id="drink-${drink}">0</span>
                    <button class="drink-btn" onclick="app.updateDrink('${drink}', 1)">+</button>
                </div>
            `;
            grid.appendChild(card);
        });
    },

    addMealItem(meal) {
        // Placeholder - would open product selector
        const productName = prompt(`Добавить продукт в ${meal}:`);
        if (productName) {
            this.addMealItemToList(meal, { product: productName });
        }
    },

    addMealItemToList(meal, item) {
        const container = document.getElementById(`meal-${meal}`);
        const div = document.createElement('div');
        div.className = 'meal-item';
        div.innerHTML = `
            <span>${item.product}${item.grams ? ` ${item.grams}г` : ''}${item.pieces ? ` ${item.pieces}шт` : ''}</span>
            <button class="meal-item-remove" onclick="this.parentElement.remove()">✕</button>
        `;
        container.appendChild(div);
    },

    updateDrink(drink, delta) {
        const current = parseInt(document.getElementById(`drink-${drink}`).textContent) || 0;
        const newVal = Math.max(0, current + delta);
        document.getElementById(`drink-${drink}`).textContent = newVal;
    },

    switchTab(tabName) {
        // Hide all panes
        document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));

        // Show selected pane
        document.getElementById(`${tabName}-pane`).classList.add('active');
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update bottom nav
        document.querySelectorAll('.nav-item').forEach(btn => {
            if (btn.dataset.tab === tabName) btn.classList.add('active');
        });
    },

    async saveEntry() {
        if (!this.token) {
            document.getElementById('tokenModal').classList.add('visible');
            return;
        }

        try {
            const date = document.getElementById('entryDate').value;
            const mealData = this.collectMealData();

            // Encrypt
            const encrypted = await encrypt(mealData, this.password);

            // Save to GitHub
            await API.saveMeal(date, encrypted, this.token);

            this.showToast('Сохранено. Дашборд обновится за ~60 сек');

            // Reload after 70 seconds
            setTimeout(() => window.location.reload(), 70000);
        } catch (err) {
            this.showError('Ошибка при сохранении: ' + err.message);
            console.error(err);
        }
    },

    collectMealData() {
        const date = document.getElementById('entryDate').value;
        const meals = {};

        this.meals.forEach(meal => {
            const items = [];
            document.querySelectorAll(`#meal-${meal} .meal-item span`).forEach(span => {
                items.push({ product: span.textContent });
            });
            meals[meal] = items;
        });

        const drinks = {};
        this.drinks.forEach(drink => {
            const count = parseInt(document.getElementById(`drink-${drink}`).textContent) || 0;
            if (count > 0) {
                drinks[drink] = count;
            }
        });

        return {
            date,
            day_of_week: new Date(date).toLocaleDateString('ru-RU', { weekday: 'short' }),
            weight_morning: parseFloat(document.getElementById('entryWeight').value) || null,
            sleep_hours: parseFloat(document.getElementById('entrySleep').value) || null,
            training: document.getElementById('entryTraining').value || null,
            binge: document.getElementById('entryBinge').value === 'true',
            mood: parseInt(document.getElementById('entryMood').value) || null,
            meals,
            drinks,
            notes: document.getElementById('entryNotes').value || null
        };
    },

    async loadEntry() {
        // TODO: Load from GitHub if exists
    },

    async loadTodayData() {
        // Load today's data from API if available
        try {
            if (this.token) {
                this.data.daily = await API.loadDailyData(this.token) || {};
                this.data.weight = await API.loadWeightData(this.token) || {};
            }
        } catch (e) {
            console.warn('Could not load data:', e);
        }
    },

    async refreshDashboard() {
        try {
            const todayEl = document.getElementById('todayCalories');
            if (!todayEl) return;

            // Find last day with data
            const dates = Object.keys(this.data.daily || {}).sort().reverse();
            const lastDate = dates[0];

            if (lastDate && this.data.daily[lastDate]) {
                const day = this.data.daily[lastDate];
                const targetEl = document.getElementById('todayTarget');
                const proteinEl = document.getElementById('todayProtein');
                const fatEl = document.getElementById('todayFat');
                const carbsEl = document.getElementById('todayCarbs');
                const fillEl = document.getElementById('progressFill');

                if (day.totals) {
                    if (todayEl) todayEl.textContent = Math.round(day.totals.kcal || 0);
                    if (targetEl) targetEl.textContent = `/ ${this.config.calorie_target} ккал`;
                    if (proteinEl) proteinEl.textContent = Math.round(day.totals.protein || 0);
                    if (fatEl) fatEl.textContent = Math.round(day.totals.fat || 0);
                    if (carbsEl) carbsEl.textContent = Math.round(day.totals.carbs || 0);

                    if (fillEl) {
                        const percent = Math.min(100, ((day.totals.kcal || 0) / this.config.calorie_target) * 100);
                        fillEl.style.width = percent + '%';
                        fillEl.className = `progress-fill ${day.zone || 'green'}`;
                    }
                }
            } else {
                if (todayEl) todayEl.textContent = '—';
                const targetEl = document.getElementById('todayTarget');
                if (targetEl) targetEl.textContent = `/ ${this.config.calorie_target} ккал`;
            }

            // Draw visualizations
            try {
                this.drawHeatmap();
            } catch (e) {
                console.warn('Heatmap draw failed:', e);
            }

            try {
                this.drawWeightChart();
            } catch (e) {
                console.warn('Weight chart draw failed:', e);
            }
        } catch (err) {
            console.warn('Dashboard refresh failed:', err);
        }
    },

    drawHeatmap() {
        const container = document.getElementById('heatmap');
        if (!container) return;

        try {
            container.innerHTML = '';
            const dates = Object.keys(this.data.daily || {}).sort();
            const lastDate = dates[dates.length - 1] || new Date().toISOString().split('T')[0];
            const today = new Date(lastDate);
            const startDate = new Date(today);
            startDate.setDate(startDate.getDate() - 60);

            for (let i = 0; i < 60; i++) {
                const date = new Date(startDate);
                date.setDate(date.getDate() + i);
                const dateStr = date.toISOString().split('T')[0];

                const cell = document.createElement('div');
                cell.className = 'heatmap-cell';

                if (this.data.daily && this.data.daily[dateStr]) {
                    const zone = this.data.daily[dateStr].zone || 'green';
                    cell.classList.add(`zone-${zone}`);
                }

                container.appendChild(cell);
            }
        } catch (e) {
            console.warn('Heatmap rendering failed:', e);
        }
    },

    drawWeightChart() {
        const canvas = document.getElementById('weightChart');
        if (!canvas || typeof Chart === 'undefined') return;

        try {
            const ctx = canvas.getContext('2d');
            const dates = Object.keys(this.data.weight || {}).sort().slice(-90);
            const weights = dates.map(d => this.data.weight[d]);

            if (dates.length === 0) {
                ctx.fillText('Нет данных о весе', 10, 20);
                return;
            }

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Вес',
                        data: weights,
                        borderColor: '#58a6ff',
                        tension: 0.3,
                        fill: false,
                        pointRadius: 0
                    }, {
                        label: 'Цель',
                        data: dates.map(() => 80),
                        borderColor: '#a371f7',
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            beginAtZero: false,
                            min: 70,
                            max: 100
                        }
                    }
                }
            });
        } catch (e) {
            console.warn('Weight chart rendering failed:', e);
        }
    },

    async saveWeight() {
        if (!this.token) {
            document.getElementById('tokenModal').classList.add('visible');
            return;
        }

        const date = document.getElementById('weightDate').value;
        const weight = parseFloat(document.getElementById('weightValue').value);

        if (!weight) {
            this.showError('Введите вес');
            return;
        }

        try {
            this.data.weight[date] = weight;
            await API.saveWeight(this.data.weight, this.token);
            this.showToast('Вес сохранён');
            document.getElementById('weightValue').value = '';
            this.refreshDashboard();
        } catch (err) {
            this.showError('Ошибка при сохранении: ' + err.message);
        }
    },

    async saveToken() {
        const tokenEl = document.getElementById('settingsToken');
        const token = tokenEl ? tokenEl.value : '';

        if (!token || token.trim() === '') {
            this.showError('Введите токен');
            return;
        }

        if (!this.password || this.password.trim() === '') {
            this.showError('Пароль не установлен. Перезагрузитесь.');
            return;
        }

        try {
            console.log('Encrypting and storing token...');
            await API.encryptAndStoreToken(token.trim(), this.password);
            this.token = token.trim();
            if (tokenEl) tokenEl.value = '';

            const statusEl = document.getElementById('tokenStatus');
            if (statusEl) statusEl.textContent = '✓ Токен сохранён';

            this.showToast('Токен сохранён успешно');
            console.log('✓ Token saved');
        } catch (err) {
            console.error('Token save failed:', err);
            this.showError('Ошибка при сохранении токена: ' + (err?.message || err));
        }
    },

    clearToken() {
        localStorage.removeItem('github_token_encrypted');
        this.token = null;
        document.getElementById('tokenStatus').textContent = '—';
        document.getElementById('settingsToken').value = '';
        this.showToast('Токен удалён');
    },

    downloadAsMarkdown() {
        // Generate markdown from form
        const date = document.getElementById('entryDate').value;
        let md = `---\ndate: ${date}\n---\n\n`;

        this.meals.forEach(meal => {
            md += `### ${meal.charAt(0).toUpperCase() + meal.slice(1)}\n`;
            document.querySelectorAll(`#meal-${meal} .meal-item span`).forEach(span => {
                md += `- ${span.textContent}\n`;
            });
            md += '\n';
        });

        const dataStr = 'data:text/markdown;charset=utf-8,' + encodeURIComponent(md);
        const link = document.createElement('a');
        link.setAttribute('href', dataStr);
        link.setAttribute('download', `${date}.md`);
        link.click();
    },

    toggleTheme() {
        const body = document.body;
        if (body.classList.contains('light-mode')) {
            body.classList.remove('light-mode');
            localStorage.setItem('theme', 'dark');
        } else {
            body.classList.add('light-mode');
            localStorage.setItem('theme', 'light');
        }
    },

    setTheme(theme) {
        if (theme === 'light') {
            document.body.classList.add('light-mode');
        } else {
            document.body.classList.remove('light-mode');
        }
    },

    confirmToken() {
        const token = document.getElementById('tokenInput').value;
        if (token) {
            this.saveToken();
            document.getElementById('tokenModal').classList.remove('visible');
            document.getElementById('settingsToken').value = token;
        }
    },

    closeTokenModal() {
        document.getElementById('tokenModal').classList.remove('visible');
    },

    clearAllData() {
        if (confirm('Очистить все локальные данные?')) {
            localStorage.clear();
            location.reload();
        }
    },

    showError(msg) {
        const errorEl = document.getElementById('passwordError');
        if (errorEl) {
            errorEl.textContent = msg;
            errorEl.style.display = 'block';
        } else {
            alert(msg);
        }
    },

    showToast(msg) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = msg;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 2500);
    }
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Set version
    document.getElementById('appVersion').textContent = '1.0.0';
});
