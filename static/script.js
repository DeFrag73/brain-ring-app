// JavaScript для адміністративної панелі Брейн-ринг

// Глобальні змінні
let currentSection = 'questions';
let editModal;

// Ініціалізація при завантаженні сторінки
document.addEventListener('DOMContentLoaded', function() {
    console.log('Адмін панель завантажена');

    // Ініціалізація Bootstrap модалів
    const editModalElement = document.getElementById('editQuestionModal');
    if (editModalElement) {
        editModal = new bootstrap.Modal(editModalElement);
    }

    // Встановлення активної секції
    showSection('questions');

    // Автоматичне оновлення статусу гри
    startGameStatusUpdates();

    // Ініціалізація подій
    initializeEventListeners();
});

// Функція для показу різних секцій
function showSection(sectionName) {
    // Сховати всі секції
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => {
        section.style.display = 'none';
    });

    // Показати обрану секцію
    const targetSection = document.getElementById(sectionName + '-section');
    if (targetSection) {
        targetSection.style.display = 'block';
    }

    // Оновити активний пункт меню
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    navLinks.forEach(link => {
        link.classList.remove('active');
    });

    const activeLink = document.querySelector(`[onclick="showSection('${sectionName}')"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }

    currentSection = sectionName;
    console.log('Переключено на секцію:', sectionName);
}

// Функція для редагування питання
function editQuestion(questionId, questionText, notes) {
    if (!editModal) {
        console.error('Модальне вікно редагування не знайдено');
        return;
    }

    // Заповнити форму
    document.getElementById('edit_question_text').value = questionText;
    document.getElementById('edit_notes').value = notes || '';

    // Встановити action для форми
    const form = document.getElementById('editQuestionForm');
    form.action = `/admin/questions/${questionId}/edit`;

    // Показати модальне вікно
    editModal.show();
}

// Функція для підтвердження видалення
function confirmDelete(itemName, deleteUrl) {
    const confirmed = confirm(`Ви впевнені, що хочете видалити "${itemName}"?`);
    if (confirmed) {
        // Створити форму для POST запиту
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = deleteUrl;
        document.body.appendChild(form);
        form.submit();
    }
}

// Ініціалізація слухачів подій
function initializeEventListeners() {
    // Обробка форм з AJAX (опціонально)
    const forms = document.querySelectorAll('form[data-ajax="true"]');
    forms.forEach(form => {
        form.addEventListener('submit', handleAjaxForm);
    });

    // Обробка кнопок з підтвердженням
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });

    // Автоматичне збереження налаштувань
    const settingsInputs = document.querySelectorAll('.auto-save');
    settingsInputs.forEach(input => {
        input.addEventListener('change', autoSaveSettings);
    });

    // Обробка клавіатурних скорочень
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

// Обробка AJAX форм
function handleAjaxForm(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    fetch(form.action, {
        method: form.method,
        body: formData
    })
    .then(response => {
        if (response.ok) {
            // Оновити сторінку або показати повідомлення
            showNotification('Дані успішно збережено', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            throw new Error('Помилка сервера');
        }
    })
    .catch(error => {
        console.error('Помилка:', error);
        showNotification('Помилка при збереженні даних', 'error');
    });
}

// Автоматичне збереження налаштувань
function autoSaveSettings(e) {
    const input = e.target;
    const key = input.getAttribute('data-setting-key');
    const value = input.value;

    // Зберегти в localStorage як резервну копію
    localStorage.setItem(`setting_${key}`, value);

    // Відправити на сервер (якщо реалізовано API)
    console.log('Збережено налаштування:', key, value);
}

// Система сповіщень
function showNotification(message, type = 'info') {
    // Створити елемент сповіщення
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Автоматично видалити через 5 секунд
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Клавіатурні скорочення
function handleKeyboardShortcuts(e) {
    // Ctrl/Cmd + число для переключення секцій
    if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '4') {
        e.preventDefault();
        const sections = ['questions', 'teams', 'game', 'stats'];
        const sectionIndex = parseInt(e.key) - 1;
        if (sections[sectionIndex]) {
            showSection(sections[sectionIndex]);
        }
    }

    // F5 для оновлення даних без перезавантаження
    if (e.key === 'F5' && e.ctrlKey) {
        e.preventDefault();
        refreshCurrentSection();
    }

    // Escape для закриття модалів
    if (e.key === 'Escape' && editModal) {
        editModal.hide();
    }
}

// Оновлення поточної секції
function refreshCurrentSection() {
    showNotification('Оновлення даних...', 'info');

    // Simulate data refresh (в реальності тут буде AJAX запит)
    setTimeout(() => {
        window.location.reload();
    }, 500);
}

// Автоматичне оновлення статусу гри
function startGameStatusUpdates() {
    // Оновлювати статус кожні 10 секунд
    setInterval(updateGameStatus, 10000);
}

function updateGameStatus() {
    // Отримати поточний статус гри
    fetch('/api/display-data')
        .then(response => response.json())
        .then(data => {
            updateGameUI(data);
        })
        .catch(error => {
            console.error('Помилка оновлення статусу гри:', error);
        });
}

function updateGameUI(data) {
    // Оновити рахунок у реальному часі (якщо на сторінці гри)
    if (currentSection === 'game') {
        const team1Score = document.querySelector('#team1-current-score');
        const team2Score = document.querySelector('#team2-current-score');

        if (team1Score) team1Score.textContent = data.team1_score || 0;
        if (team2Score) team2Score.textContent = data.team2_score || 0;
    }
}

// Утиліти для роботи з командами
const TeamManager = {
    // Перевірити чи грали команди між собою
    haveTeamsPlayed: function(team1Id, team2Id) {
        // Цей метод буде реалізовано через API запит до сервера
        return fetch(`/api/teams-played?team1=${team1Id}&team2=${team2Id}`)
            .then(response => response.json())
            .then(data => data.played)
            .catch(error => {
                console.error('Помилка перевірки історії ігор:', error);
                return false;
            });
    },

    // Отримати рекомендовані пари команд
    getRecommendedPairs: function() {
        return fetch('/api/recommended-pairs')
            .then(response => response.json())
            .catch(error => {
                console.error('Помилка отримання рекомендацій:', error);
                return [];
            });
    },

    // Показати рекомендації адміністратору
    showRecommendations: function() {
        this.getRecommendedPairs().then(pairs => {
            if (pairs.length === 0) {
                showNotification('Всі команди вже грали між собою', 'info');
                return;
            }

            const recommendations = pairs.map(pair =>
                `${pair.team1_name} vs ${pair.team2_name}`
            ).join('<br>');

            showNotification(`Рекомендовані пари:<br>${recommendations}`, 'info');
        });
    }
};

// Утиліти для роботи з питаннями
const QuestionManager = {
    // Швидке додавання питання
    quickAdd: function() {
        const text = prompt('Введіть текст питання:');
        if (text && text.trim()) {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/admin/questions/add';

            const textInput = document.createElement('input');
            textInput.type = 'hidden';
            textInput.name = 'question_text';
            textInput.value = text.trim();

            const notesInput = document.createElement('input');
            notesInput.type = 'hidden';
            notesInput.name = 'notes';
            notesInput.value = '';

            form.appendChild(textInput);
            form.appendChild(notesInput);
            document.body.appendChild(form);
            form.submit();
        }
    },

    // Масове позначення питань як використані
    markAllUsed: function() {
        if (confirm('Позначити всі питання як використані?')) {
            const forms = document.querySelectorAll('form[action*="toggle-used"]');
            forms.forEach(form => {
                const button = form.querySelector('button');
                if (button && button.classList.contains('btn-secondary')) {
                    form.submit();
                }
            });
        }
    },

    // Скидання всіх питань
    resetAllQuestions: function() {
        if (confirm('Скинути статус всіх питань (позначити як невикористані)?')) {
            // Реалізувати через API
            fetch('/api/questions/reset-all', { method: 'POST' })
                .then(response => {
                    if (response.ok) {
                        showNotification('Статус питань скинуто', 'success');
                        setTimeout(() => window.location.reload(), 1000);
                    }
                })
                .catch(error => {
                    console.error('Помилка скидання питань:', error);
                    showNotification('Помилка при скиданні', 'error');
                });
        }
    },

    // Імпорт питань з файлу
    importQuestions: function() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.txt,.csv';
        input.onchange = function(e) {
            const file = e.target.files[0];
            if (file) {
                QuestionManager.processImportFile(file);
            }
        };
        input.click();
    },

    // Обробка файлу з питаннями
    processImportFile: function(file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const content = e.target.result;
            const questions = content.split('\n').filter(q => q.trim());

            if (questions.length === 0) {
                showNotification('Файл не містить питань', 'error');
                return;
            }

            if (confirm(`Знайдено ${questions.length} питань. Імпортувати?`)) {
                QuestionManager.bulkAddQuestions(questions);
            }
        };
        reader.readAsText(file);
    },

    // Масове додавання питань
    bulkAddQuestions: function(questions) {
        const promises = questions.map((questionText, index) => {
            const formData = new FormData();
            formData.append('question_text', questionText.trim());
            formData.append('notes', `Імпорт ${new Date().toLocaleDateString()}`);

            return fetch('/admin/questions/add', {
                method: 'POST',
                body: formData
            });
        });

        Promise.all(promises)
            .then(() => {
                showNotification(`Імпортовано ${questions.length} питань`, 'success');
                setTimeout(() => window.location.reload(), 2000);
            })
            .catch(error => {
                console.error('Помилка імпорту:', error);
                showNotification('Помилка при імпорті питань', 'error');
            });
    }
};

// Утиліти для статистики
const StatsManager = {
    // Експорт статистики
    exportStats: function() {
        fetch('/api/stats/export')
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `brainring_stats_${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            })
            .catch(error => {
                console.error('Помилка експорту:', error);
                showNotification('Помилка при експорті статистики', 'error');
            });
    },

    // Оновити статистику
    refresh: function() {
        const statsSection = document.getElementById('stats-section');
        if (statsSection) {
            statsSection.classList.add('loading');
            setTimeout(() => {
                window.location.reload();
            }, 500);
        }
    }
};

// Утиліти для управління грою
const GameManager = {
    // Швидкий старт гри з випадковими командами
    quickStart: function() {
        const teamSelects = document.querySelectorAll('select[name*="team"]');
        const teams = [];

        teamSelects[0].querySelectorAll('option').forEach(option => {
            if (option.value) teams.push(option.value);
        });

        if (teams.length < 2) {
            showNotification('Недостатньо команд для гри', 'error');
            return;
        }

        // Вибрати дві випадкові команди
        const shuffled = teams.sort(() => 0.5 - Math.random());
        const team1 = shuffled[0];
        const team2 = shuffled[1];

        // Встановити значення
        if (teamSelects[0]) teamSelects[0].value = team1;
        if (teamSelects[1]) teamSelects[1].value = team2;

        // Підтвердити вибір
        if (confirm('Розпочати гру з випадково обраними командами?')) {
            teamSelects[0].closest('form').submit();
        }
    },

    // Таймер для питання
    startQuestionTimer: function(seconds = 60) {
        let timeLeft = seconds;
        const timerElement = document.getElementById('question-timer');

        if (!timerElement) {
            // Створити елемент таймера
            const timer = document.createElement('div');
            timer.id = 'question-timer';
            timer.className = 'alert alert-info position-fixed';
            timer.style.cssText = 'top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999;';
            document.body.appendChild(timer);
        }

        const interval = setInterval(() => {
            const timer = document.getElementById('question-timer');
            if (timer) {
                timer.textContent = `Залишилось часу: ${timeLeft} сек`;

                if (timeLeft <= 10) {
                    timer.className = 'alert alert-danger position-fixed';
                }

                timeLeft--;

                if (timeLeft < 0) {
                    clearInterval(interval);
                    timer.textContent = 'Час вичерпано!';
                    setTimeout(() => timer.remove(), 3000);
                }
            } else {
                clearInterval(interval);
            }
        }, 1000);

        // Зупинити таймер при кліку
        document.getElementById('question-timer').onclick = function() {
            clearInterval(interval);
            this.remove();
        };
    }
};

// Розширені функції адмінської панелі
const AdminPanel = {
    // Ініціалізація розширених функцій
    init: function() {
        this.addToolbar();
        this.addKeyboardHelp();
        this.initializeTheme();
    },

    // Додати панель інструментів
    addToolbar: function() {
        const toolbar = document.createElement('div');
        toolbar.className = 'admin-toolbar position-fixed';
        toolbar.style.cssText = 'bottom: 20px; right: 20px; z-index: 1000;';
        toolbar.innerHTML = `
            <div class="btn-group-vertical" role="group">
                <button type="button" class="btn btn-sm btn-primary" onclick="QuestionManager.quickAdd()" title="Швидко додати питання">
                    <i class="fas fa-plus"></i>
                </button>
                <button type="button" class="btn btn-sm btn-info" onclick="GameManager.quickStart()" title="Швидкий старт">
                    <i class="fas fa-play"></i>
                </button>
                <button type="button" class="btn btn-sm btn-secondary" onclick="AdminPanel.toggleTheme()" title="Змінити тему">
                    <i class="fas fa-palette"></i>
                </button>
                <button type="button" class="btn btn-sm btn-success" onclick="window.open('/display', '_blank')" title="Екран глядачів">
                    <i class="fas fa-tv"></i>
                </button>
            </div>
        `;
        document.body.appendChild(toolbar);
    },

    // Додати довідку по клавішам
    addKeyboardHelp: function() {
        document.addEventListener('keydown', function(e) {
            if (e.key === 'F1') {
                e.preventDefault();
                AdminPanel.showKeyboardHelp();
            }
        });
    },

    // Показати довідку
    showKeyboardHelp: function() {
        const helpModal = `
            <div class="modal fade" id="helpModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Клавіатурні скорочення</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <ul>
                                <li><kbd>Ctrl+1</kbd> - Питання</li>
                                <li><kbd>Ctrl+2</kbd> - Команди</li>
                                <li><kbd>Ctrl+3</kbd> - Поточна гра</li>
                                <li><kbd>Ctrl+4</kbd> - Статистика</li>
                                <li><kbd>F1</kbd> - Ця довідка</li>
                                <li><kbd>F5</kbd> - Оновити дані</li>
                                <li><kbd>Escape</kbd> - Закрити модальні вікна</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', helpModal);
        new bootstrap.Modal(document.getElementById('helpModal')).show();
    },

    // Ініціалізація теми
    initializeTheme: function() {
        const savedTheme = localStorage.getItem('admin_theme') || 'light';
        document.body.setAttribute('data-theme', savedTheme);
    },

    // Переключення теми
    toggleTheme: function() {
        const currentTheme = document.body.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';

        document.body.setAttribute('data-theme', newTheme);
        localStorage.setItem('admin_theme', newTheme);

        showNotification(`Тема змінена на ${newTheme === 'dark' ? 'темну' : 'світлу'}`, 'info');
    }
};

// Система резервного копіювання
const BackupManager = {
    // Створити резервну копію
    createBackup: function() {
        fetch('/api/backup/create', { method: 'POST' })
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `brainring_backup_${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                showNotification('Резервну копію створено', 'success');
            })
            .catch(error => {
                console.error('Помилка створення копії:', error);
                showNotification('Помилка при створенні резервної копії', 'error');
            });
    },

    // Відновити з резервної копії
    restoreBackup: function() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.onchange = function(e) {
            const file = e.target.files[0];
            if (file && confirm('УВАГА! Це замінить всі поточні дані. Продовжити?')) {
                const formData = new FormData();
                formData.append('backup', file);

                fetch('/api/backup/restore', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (response.ok) {
                        showNotification('Дані відновлено з резервної копії', 'success');
                        setTimeout(() => window.location.reload(), 2000);
                    } else {
                        throw new Error('Помилка відновлення');
                    }
                })
                .catch(error => {
                    console.error('Помилка відновлення:', error);
                    showNotification('Помилка при відновленні з резервної копії', 'error');
                });
            }
        };
        input.click();
    }
};

// Ініціалізація розширених функцій після завантаження DOM
document.addEventListener('DOMContentLoaded', function() {
    AdminPanel.init();
});

// Експорт для глобального використання
window.BrainRingAdmin = {
    showSection,
    editQuestion,
    confirmDelete,
    showNotification,
    TeamManager,
    QuestionManager,
    StatsManager,
    GameManager,
    AdminPanel,
    BackupManager
};

console.log('Скрипт адмін панелі завантажено успішно');