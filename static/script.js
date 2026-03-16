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

    // Відновлення активної секції: пріоритет — URL параметр > localStorage > 'questions'
    const urlParams = new URLSearchParams(window.location.search);
    const sectionFromUrl = urlParams.get('section');
    const sectionFromStorage = localStorage.getItem('activeSection');
    const initialSection = sectionFromUrl || sectionFromStorage || 'questions';
    showSection(initialSection);

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

    // Зберегти активну секцію в localStorage
    localStorage.setItem('activeSection', sectionName);

    console.log('Переключено на секцію:', sectionName);
}

// Оновлена функція для редагування питання з підтримкою складності
function editQuestion(questionId, questionText, notes, difficulty) {
    if (!editModal) {
        console.error('Модальне вікно редагування не знайдено');
        return;
    }

    // Заповнити форму
    document.getElementById('edit_question_text').value = questionText;
    document.getElementById('edit_notes').value = notes || '';
    document.getElementById('edit_difficulty').value = difficulty || 'medium';

    // Встановити action для форми
    const form = document.getElementById('editQuestionForm');
    form.action = `/admin/questions/${questionId}/edit`;

    // Показати модальне вікно
    editModal.show();
}

// Функція перенумерації питань
function renumberQuestions() {
    if (confirm('Перенумерувати всі питання за порядком створення?')) {
        fetch('/admin/questions/renumber', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('Питання успішно перенумеровано', 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                throw new Error('Помилка сервера');
            }
        })
        .catch(error => {
            console.error('Помилка перенумерації:', error);
            showNotification('Помилка при перенумерації питань', 'error');
        });
    }
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

    // Валідація форми вибору команд
    const setTeamsForm = document.getElementById('set-teams-form');
    if (setTeamsForm) {
        setTeamsForm.addEventListener('submit', validateTeamsSelection);
    }

    // Перевірка помилки з URL параметрів
    checkTeamsError();
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
    // Швидке додавання питання з вибором складності через модальне вікно
    quickAdd: function() {
        const modalElement = document.getElementById('quickAddModal');
        if (!modalElement) {
            console.error('Модальне вікно швидкого додавання не знайдено');
            return;
        }

        // Очистити попередні значення
        document.getElementById('quick_question_text').value = '';
        document.getElementById('quick_difficulty').value = 'medium';

        const modal = new bootstrap.Modal(modalElement);
        modal.show();

        // Автофокус на поле тексту
        modalElement.addEventListener('shown.bs.modal', function () {
            document.getElementById('quick_question_text').focus();
        }, { once: true });
    },

    // Масове позначення питань за складністю
    markByDifficulty: function(difficulty, markAsUsed = true) {
        const message = `Позначити всі питання рівня "${difficulty}" як ${markAsUsed ? 'використані' : 'невикористані'}?`;
        if (confirm(message)) {
            const forms = document.querySelectorAll('form[action*="toggle-used"]');
            let count = 0;

            forms.forEach(form => {
                const row = form.closest('tr');
                const difficultyBadge = row.querySelector('.badge');
                const isUsedBadge = row.querySelector('.badge.bg-secondary');

                if (difficultyBadge && difficultyBadge.textContent.toLowerCase().includes(difficulty.toLowerCase())) {
                    const shouldToggle = markAsUsed ? !isUsedBadge : isUsedBadge;
                    if (shouldToggle) {
                        setTimeout(() => form.submit(), count * 100); // Затримка для уникнення перевантаження
                        count++;
                    }
                }
            });

            if (count > 0) {
                showNotification(`Буде оброблено ${count} питань`, 'info');
            } else {
                showNotification('Не знайдено підходящих питань', 'warning');
            }
        }
    },

    // Скидання всіх питань
    resetAllQuestions: function() {
        if (confirm('Скинути статус всіх питань (позначити як невикористані)?')) {
            fetch('/api/questions/reset-all', { method: 'POST' })
                .then(response => {
                    if (response.ok) {
                        showNotification('Статус питань скинуто', 'success');
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        throw new Error('Помилка сервера');
                    }
                })
                .catch(error => {
                    console.error('Помилка скидання питань:', error);
                    showNotification('Помилка при скиданні', 'error');
                });
        }
    },

    // Імпорт питань з файлу з підтримкою складності
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
            let questions = [];

            if (file.name.endsWith('.csv')) {
                // Обробка CSV формату: "Текст питання","Складність","Нотатки"
                const lines = content.split('\n').filter(line => line.trim());
                questions = lines.map(line => {
                    const parts = line.split(',').map(part => part.replace(/"/g, '').trim());
                    return {
                        text: parts[0] || '',
                        difficulty: parts[1] || 'medium',
                        notes: parts[2] || ''
                    };
                }).filter(q => q.text);
            } else {
                // Обробка TXT формату: кожен рядок = питання з середньою складністю
                const lines = content.split('\n').filter(line => line.trim());
                questions = lines.map(line => ({
                    text: line.trim(),
                    difficulty: 'medium',
                    notes: `Імпорт ${new Date().toLocaleDateString()}`
                }));
            }

            if (questions.length === 0) {
                showNotification('Файл не містить питань', 'error');
                return;
            }

            // Показати попередній перегляд
            QuestionManager.showImportPreview(questions);
        };
        reader.readAsText(file);
    },

    // Показати попередній перегляд імпорту
    showImportPreview: function(questions) {
        const previewHtml = `
            <div class="modal fade" id="importPreviewModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Попередній перегляд імпорту</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>Знайдено <strong>${questions.length}</strong> питань:</p>
                            <div style="max-height: 300px; overflow-y: auto;">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Питання</th>
                                            <th>Складність</th>
                                            <th>Нотатки</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${questions.slice(0, 10).map(q => `
                                            <tr>
                                                <td>${q.text.substring(0, 50)}${q.text.length > 50 ? '...' : ''}</td>
                                                <td><span class="badge bg-info">${q.difficulty}</span></td>
                                                <td>${q.notes}</td>
                                            </tr>
                                        `).join('')}
                                        ${questions.length > 10 ? `<tr><td colspan="3" class="text-center">... і ще ${questions.length - 10}</td></tr>` : ''}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Скасувати</button>
                            <button type="button" class="btn btn-primary" onclick="QuestionManager.bulkAddQuestions(${JSON.stringify(questions).replace(/"/g, '&quot;')})">
                                Імпортувати всі
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', previewHtml);
        const modal = new bootstrap.Modal(document.getElementById('importPreviewModal'));
        modal.show();

        // Видалити модальне вікно після закриття
        document.getElementById('importPreviewModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    },

    // Масове додавання питань з підтримкою складності
    bulkAddQuestions: function(questions) {
        const modal = bootstrap.Modal.getInstance(document.getElementById('importPreviewModal'));
        if (modal) modal.hide();

        showNotification('Починаю імпорт питань...', 'info');

        const promises = questions.map((question, index) => {
            const formData = new FormData();
            formData.append('question_text', question.text);
            formData.append('difficulty', question.difficulty || 'medium');
            formData.append('notes', question.notes || `Імпорт ${new Date().toLocaleDateString()}`);

            return new Promise((resolve, reject) => {
                setTimeout(() => {
                    fetch('/admin/questions/add', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => {
                        if (response.ok) {
                            resolve();
                        } else {
                            reject(new Error(`Помилка для питання ${index + 1}`));
                        }
                    })
                    .catch(reject);
                }, index * 200); // Затримка між запитами
            });
        });

        Promise.allSettled(promises)
            .then(results => {
                const successful = results.filter(r => r.status === 'fulfilled').length;
                const failed = results.length - successful;

                if (failed === 0) {
                    showNotification(`Успішно імпортовано ${successful} питань`, 'success');
                } else {
                    showNotification(`Імпортовано ${successful} питань, помилок: ${failed}`, 'warning');
                }

                setTimeout(() => window.location.reload(), 2000);
            });
    },

    // Експорт питань в CSV
    exportQuestions: function() {
        fetch('/api/questions/export')
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `brainring_questions_${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                showNotification('Питання експортовано', 'success');
            })
            .catch(error => {
                console.error('Помилка експорту:', error);
                showNotification('Помилка при експорті питань', 'error');
            });
    },

    // Оновлення статистики складності в реальному часі
    updateDifficultyStats: function() {
        fetch('/api/difficulty-stats')
            .then(response => response.json())
            .then(stats => {
                // Оновити статистику на сторінці
                Object.keys(stats).forEach(difficulty => {
                    const stat = stats[difficulty];
                    const element = document.querySelector(`[data-difficulty="${difficulty}"]`);
                    if (element) {
                        element.querySelector('.available-count').textContent = stat.available;
                        element.querySelector('.total-count').textContent = stat.total;
                    }
                });
                showNotification('Статистику оновлено', 'success');
            })
            .catch(error => {
                console.error('Помилка оновлення статистики:', error);
            });
    }
};

// Розширені функції сортування та фільтрації
const QuestionFilter = {
    activeFilters: {
        search: '',
        difficulty: '',
        status: ''
    },

    // Застосувати всі фільтри одночасно
    applyAllFilters: function() {
        const rows = document.querySelectorAll('#questions-section tbody tr');
        let visibleCount = 0;

        rows.forEach(row => {
            let isVisible = true;

            // Фільтр за пошуковим запитом
            if (this.activeFilters.search) {
                const questionText = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
                const notes = row.querySelector('td:nth-child(4)').textContent.toLowerCase();
                const lowerQuery = this.activeFilters.search.toLowerCase();

                if (!questionText.includes(lowerQuery) && !notes.includes(lowerQuery)) {
                    isVisible = false;
                }
            }

            // Фільтр за складністю
            if (this.activeFilters.difficulty && isVisible) {
                const difficultyBadge = row.querySelector('td:nth-child(3) .badge');
                if (!difficultyBadge || !difficultyBadge.textContent.toLowerCase().includes(this.activeFilters.difficulty.toLowerCase())) {
                    isVisible = false;
                }
            }

            // Фільтр за статусом
            if (this.activeFilters.status && isVisible) {
                const statusBadge = row.querySelector('td:nth-child(5) .badge');
                if (this.activeFilters.status === 'used') {
                    if (!statusBadge || !statusBadge.classList.contains('bg-secondary')) {
                        isVisible = false;
                    }
                } else if (this.activeFilters.status === 'available') {
                    if (!statusBadge || !statusBadge.classList.contains('bg-success')) {
                        isVisible = false;
                    }
                }
            }

            row.style.display = isVisible ? '' : 'none';
            if (isVisible) visibleCount++;
        });

        // Оновити бейджі активних фільтрів
        this.updateFilterBadges();

        // Оновити лічильник результатів
        this.updateResultsCount(visibleCount, rows.length);
    },

    // Встановити фільтр пошуку
    setSearchFilter: function(query) {
        this.activeFilters.search = query;
        this.applyAllFilters();
    },

    // Встановити фільтр складності
    setDifficultyFilter: function(difficulty) {
        this.activeFilters.difficulty = difficulty;
        this.applyAllFilters();
    },

    // Встановити фільтр статусу
    setStatusFilter: function(status) {
        this.activeFilters.status = status;
        this.applyAllFilters();
    },

    // Видалити конкретний фільтр
    removeFilter: function(filterType) {
        this.activeFilters[filterType] = '';

        // Очистити відповідне поле вводу
        if (filterType === 'search') {
            const searchInput = document.getElementById('search-questions');
            if (searchInput) searchInput.value = '';
        } else if (filterType === 'difficulty') {
            const difficultySelect = document.getElementById('filter-difficulty');
            if (difficultySelect) difficultySelect.value = '';
        } else if (filterType === 'status') {
            const statusSelect = document.getElementById('filter-status');
            if (statusSelect) statusSelect.value = '';
        }

        this.applyAllFilters();
    },

    // Очистити всі фільтри
    clearAllFilters: function() {
        this.activeFilters = {
            search: '',
            difficulty: '',
            status: ''
        };

        // Очистити всі поля
        const searchInput = document.getElementById('search-questions');
        if (searchInput) searchInput.value = '';

        const difficultySelect = document.getElementById('filter-difficulty');
        if (difficultySelect) difficultySelect.value = '';

        const statusSelect = document.getElementById('filter-status');
        if (statusSelect) statusSelect.value = '';

        this.applyAllFilters();
    },

    // Оновити бейджі активних фільтрів
    updateFilterBadges: function() {
        const container = document.getElementById('active-filters-container');
        if (!container) return;

        container.innerHTML = '';

        // Додати бейдж для пошуку
        if (this.activeFilters.search) {
            container.appendChild(this.createFilterBadge(
                'search',
                `Пошук: "${this.activeFilters.search}"`,
                'primary'
            ));
        }

        // Додати бейдж для складності
        if (this.activeFilters.difficulty) {
            container.appendChild(this.createFilterBadge(
                'difficulty',
                `Складність: ${this.activeFilters.difficulty}`,
                'info'
            ));
        }

        // Додати бейдж для статусу
        if (this.activeFilters.status) {
            const statusText = this.activeFilters.status === 'used' ? 'Використані' : 'Доступні';
            container.appendChild(this.createFilterBadge(
                'status',
                `Статус: ${statusText}`,
                'warning'
            ));
        }

        // Показати/сховати контейнер
        const hasFilters = this.activeFilters.search || this.activeFilters.difficulty || this.activeFilters.status;
        container.style.display = hasFilters ? 'flex' : 'none';
    },

    // Створити бейдж фільтра
    createFilterBadge: function(filterType, text, colorClass) {
        const badge = document.createElement('span');
        badge.className = `badge bg-${colorClass} me-2 mb-2 d-inline-flex align-items-center`;
        badge.style.fontSize = '0.9rem';
        badge.style.padding = '0.5rem 0.75rem';
        badge.style.cursor = 'default';

        const textSpan = document.createElement('span');
        textSpan.textContent = text;
        textSpan.style.marginRight = '0.5rem';

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close btn-close-white';
        closeBtn.style.fontSize = '0.6rem';
        closeBtn.style.padding = '0';
        closeBtn.style.marginLeft = '0.5rem';
        closeBtn.onclick = () => this.removeFilter(filterType);

        badge.appendChild(textSpan);
        badge.appendChild(closeBtn);

        return badge;
    },

    // Оновити лічильник результатів
    updateResultsCount: function(visible, total) {
        const counter = document.getElementById('results-counter');
        if (!counter) return;

        if (visible === total) {
            counter.innerHTML = `<small class="text-muted">Показано всі ${total} питань</small>`;
        } else {
            counter.innerHTML = `<small class="text-success"><strong>Знайдено: ${visible}</strong> з ${total} питань</small>`;
        }
    },

    // Застарілі методи для зворотної сумісності
    filterByDifficulty: function(difficulty) {
        this.setDifficultyFilter(difficulty);
    },

    filterByStatus: function(status) {
        this.setStatusFilter(status);
    },

    searchQuestions: function(query) {
        this.setSearchFilter(query);
    },

    clearFilters: function() {
        this.clearAllFilters();
    }
};

// Функція пошуку питань
function performQuestionSearch() {
    const query = document.getElementById('search-questions').value;
    QuestionFilter.setSearchFilter(query);
}

// Ініціалізація при завантаженні
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-questions');
    if (searchInput) {
        // Пошук при введенні тексту з затримкою
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performQuestionSearch();
            }, 300);
        });

        // Пошук при натисканні Enter
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                performQuestionSearch();
            }
        });
    }

    // Слухачі для селектів фільтрів
    const difficultySelect = document.getElementById('filter-difficulty');
    if (difficultySelect) {
        difficultySelect.addEventListener('change', function() {
            QuestionFilter.setDifficultyFilter(this.value);
        });
    }

    const statusSelect = document.getElementById('filter-status');
    if (statusSelect) {
        statusSelect.addEventListener('change', function() {
            QuestionFilter.setStatusFilter(this.value);
        });
    }
});

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

// Функція валідації вибору команд
function validateTeamsSelection(e) {
    const team1Select = document.getElementById('team1_id');
    const team2Select = document.getElementById('team2_id');
    const errorAlert = document.getElementById('team-error-alert');

    const team1Id = team1Select.value;
    const team2Id = team2Select.value;

    // Перевірка, що обрано дві різні команди
    if (team1Id && team2Id && team1Id === team2Id) {
        e.preventDefault(); // Запобігаємо відправці форми

        // Показуємо повідомлення про помилку
        errorAlert.classList.remove('d-none');

        // Додаємо червоне виділення до select елементів
        team1Select.classList.add('is-invalid');
        team2Select.classList.add('is-invalid');

        // Прокручуємо до помилки
        errorAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Показуємо системне сповіщення
        showNotification('Команда не може грати сама з собою', 'error');

        return false;
    }

    // Ховаємо повідомлення про помилку якщо все ок
    errorAlert.classList.add('d-none');
    team1Select.classList.remove('is-invalid');
    team2Select.classList.remove('is-invalid');

    return true;
}

// Функція для перевірки помилки з URL параметрів
function checkTeamsError() {
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');

    if (error === 'same_teams') {
        const errorAlert = document.getElementById('team-error-alert');
        const team1Select = document.getElementById('team1_id');
        const team2Select = document.getElementById('team2_id');

        if (errorAlert) {
            // Показуємо помилку
            errorAlert.classList.remove('d-none');

            if (team1Select) team1Select.classList.add('is-invalid');
            if (team2Select) team2Select.classList.add('is-invalid');

            // Прокручуємо до секції гри
            showSection('game');

            // Показуємо системне сповіщення
            setTimeout(() => {
                showNotification('Команда не може грати сама з собою', 'error');
                errorAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 500);
        }
    }
}

// Додаємо слухачів на зміну select для автоматичного приховування помилки
document.addEventListener('DOMContentLoaded', function() {
    const team1Select = document.getElementById('team1_id');
    const team2Select = document.getElementById('team2_id');
    const errorAlert = document.getElementById('team-error-alert');

    if (team1Select && team2Select && errorAlert) {
        const hideError = function() {
            errorAlert.classList.add('d-none');
            team1Select.classList.remove('is-invalid');
            team2Select.classList.remove('is-invalid');
        };

        team1Select.addEventListener('change', hideError);
        team2Select.addEventListener('change', hideError);
    }
});

console.log('Скрипт адмін панелі завантажено успішно');