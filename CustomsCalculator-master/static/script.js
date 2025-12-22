function app() {
    return {
        searchQuery: '',
        searchResults: [],

        // Флаги отображения полей
        showEngineVolume: false,
        showAutoFields: false,
        showPowerHp: false,

        countries: [],
        loading: false,
        errorMsg: null,
        result: null,

        selectedUnitType: 'none',
        selectedUnitLabel: '',

        form: {
            tn_code: '',
            customs_value: null,
            weight_kg: 0,
            quantity_pcs: 0,
            liter_qty: 0,
            volume_cm3: 0,
            manufacturing_year: new Date().getFullYear(), // По умолчанию текущий год
            power_hp: 0,
            origin_country_code: ''
        },

        unitMapping: {
            'pcs': { type: 'qty', label: 'Количество (штук)' },
            '100_pcs': { type: 'qty', label: 'Количество (штук)' },
            '1000_pcs': { type: 'qty', label: 'Количество (штук)' },
            'pair': { type: 'qty', label: 'Количество (пар)' },
            'l': { type: 'liters', label: 'Объем (литров)' },
            'ml': { type: 'liters', label: 'Объем (литров)' },
            '1000_l': { type: 'liters', label: 'Объем (литров)' },
            'l_alc_100': { type: 'liters', label: 'Объем (литров спирта)' },
            'm3': { type: 'volume', label: 'Объем (м³)' },
            '1000_kwh': { type: 'other', label: 'Количество (кВт.ч)' },
            'cm3': {type: 'other', label: 'Объем двигателя (см3)' },
            'm': { type: 'other', label: 'Длина (метров)' },
            'm2': { type: 'other', label: 'Площадь (м²)' },
            '1000_m2': { type: 'other', label: 'Площадь (м²)' },
            'carat': { type: 'other', label: 'Караты' },
            'ci': { type: 'other', label: 'Кюри' },
            'g': { type: 'none', label: '' },
            'kg': { type: 'none', label: '' },
            't': { type: 'none', label: '' }
        },

        async init() {
            try {
                const res = await fetch('/api/v1/countries');
                if (res.ok) this.countries = await res.json();
            } catch (e) { console.error("Ошибка загрузки стран"); }
        },

        async searchGoods() {
            if (this.searchQuery.length < 2) return;
            try {
                const res = await fetch(`/api/v1/tnved/search?q=${this.searchQuery}&limit=20`);
                if (res.ok) this.searchResults = await res.json();
            } catch(e) { console.error("Ошибка поиска"); }
        },

        selectCode(item) {
            this.form.tn_code = item.code;
            this.searchResults = [];
            this.searchQuery = `${item.code} — ${item.description.substring(0, 40)}${item.description.length>40?'...':''}`;

            // 1. Определение единиц измерения (для специфических пошлин)
            let unitCode = item.unit2;
            if (!unitCode || unitCode === 'null') {
                unitCode = item.unit;
            }

            if (unitCode && this.unitMapping[unitCode]) {
                const map = this.unitMapping[unitCode];
                this.selectedUnitType = map.type;
                this.selectedUnitLabel = map.label;
            } else {
                this.selectedUnitType = 'none';
                this.selectedUnitLabel = '';
            }

            // 2. Логика для Утилизационного сбора и Авто
            // Мы смотрим в calc_metadata, который пришел с бэкенда
            const meta = item.calc_metadata || {};
            const type = meta.type;

            this.showAutoFields = false;
            this.showEngineVolume = false;
            this.showPowerHp = false;

            // Если это транспорт (легковые, грузовики, тракторы, спецтехника)
            if (['M1', 'N', 'tractor', 'special'].includes(type)) {
                this.showAutoFields = true;

                // Для тракторов и спецтехники просим Мощность
                if (type === 'tractor' || type === 'special') {
                    this.showPowerHp = true;
                }

                // Для легковых (M1) просим Объем, если это не чистый электро
                if (type === 'M1' && meta.engine_type !== 'electric') {
                    this.showEngineVolume = true;
                }
            }

            // Дополнительная проверка: иногда пошлина зависит от см3, даже если это не авто (редко)
            // или если метаданные пусты, но в ставках есть cm3
            if (!this.showEngineVolume && item.rates && Array.isArray(item.rates)) {
                if (item.rates.some(r => r.specific_unit === 'cm3')) {
                    this.showAutoFields = true; // Показываем блок авто
                    this.showEngineVolume = true;
                }
            }

            // Сброс значений формы
            this.form.quantity_pcs = 0;
            this.form.liter_qty = 0;
            this.form.volume_cm3 = 0;
            this.form.power_hp = 0;
            this.form.manufacturing_year = new Date().getFullYear();
        },

        get isValid() {
            return this.form.tn_code && this.form.customs_value > 0 && this.form.weight_kg >= 0;
        },

        async calculate() {
            this.loading = true;
            this.errorMsg = null;
            this.result = null;

            try {
                const res = await fetch('/api/v1/calculate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(this.form)
                });

                const data = await res.json();

                if (!res.ok) {
                    if (data.detail && Array.isArray(data.detail)) {
                        this.errorMsg = data.detail.map(e => e.msg).join(', ');
                    } else {
                        this.errorMsg = data.detail || data.error || "Произошла ошибка при расчете";
                    }
                } else {
                    this.result = data;
                }
            } catch (e) {
                this.errorMsg = "Не удалось соединиться с сервером";
            } finally {
                this.loading = false;
            }
        },

        formatMoney(amount, currency = 'UZS') {
            if (amount === undefined || amount === null) return '0';
            let val = new Intl.NumberFormat('ru-RU', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount);
            return currency === 'USD' ? `$ ${val}` : `${val} сўм`;
        }
    }
}