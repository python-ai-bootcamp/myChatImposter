import React, { useState, useEffect, useRef } from 'react';

// Styles for the modal and picker
const styles = {
    container: {
        fontFamily: 'sans-serif',
    },
    summaryContainer: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
    },
    summaryText: {
        padding: '2px 8px',
        backgroundColor: '#f5f5f5',
        border: '1px solid #ddd',
        borderRadius: '4px',
        minWidth: '150px',
        fontSize: '0.8rem',
        lineHeight: '1.2',
        color: '#333',
    },
    editButton: {
        padding: '2px 8px',
        backgroundColor: '#007bff',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '0.8rem',
        lineHeight: '1.2',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
    },
    modalOverlay: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.5)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
    },
    modalContent: {
        backgroundColor: 'white',
        padding: '20px',
        borderRadius: '8px',
        width: '400px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
    },
    tabs: {
        display: 'flex',
        borderBottom: '1px solid #ddd',
        marginBottom: '20px',
    },
    tab: (isActive) => ({
        padding: '10px 15px',
        cursor: 'pointer',
        borderBottom: isActive ? '2px solid #007bff' : 'none',
        color: isActive ? '#007bff' : '#666',
        fontWeight: isActive ? 'bold' : 'normal',
    }),
    formGroup: {
        marginBottom: '15px',
    },
    label: {
        display: 'block',
        marginBottom: '5px',
        fontWeight: '500',
        fontSize: '0.9rem',
    },
    input: {
        padding: '8px',
        border: '1px solid #ddd',
        borderRadius: '4px',
        width: '100%',
        boxSizing: 'border-box',
    },
    timeInput: {
        padding: '8px',
        border: '1px solid #ddd',
        borderRadius: '4px',
        width: '120px',
    },
    dayOfWeekContainer: {
        display: 'flex',
        flexWrap: 'wrap',
        gap: '10px',
    },
    checkboxLabel: {
        display: 'flex',
        alignItems: 'center',
        gap: '5px',
        fontSize: '0.9rem',
        cursor: 'pointer',
    },
    footer: {
        display: 'flex',
        justifyContent: 'flex-end',
        gap: '10px',
        marginTop: '20px',
        borderTop: '1px solid #eee',
        paddingTop: '15px',
    },
    cancelButton: {
        padding: '8px 16px',
        backgroundColor: '#fff',
        color: '#dc3545',
        border: '1px solid #dc3545',
        borderRadius: '4px',
        cursor: 'pointer',
        fontWeight: '500',
    },
    saveButton: {
        padding: '8px 16px',
        backgroundColor: '#007bff',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
    },
};

const DAYS = [
    { label: 'Sun', value: '0' },
    { label: 'Mon', value: '1' },
    { label: 'Tue', value: '2' },
    { label: 'Wed', value: '3' },
    { label: 'Thu', value: '4' },
    { label: 'Fri', value: '5' },
    { label: 'Sat', value: '6' },
];

const CronPickerWidget = (props) => {
    const { value, onChange, required } = props;
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [activeTab, setActiveTab] = useState('daily'); // daily, weekly, custom

    // State for builder
    const [time, setTime] = useState('20:00');
    const [selectedDays, setSelectedDays] = useState(['1']); // Default Monday
    const [customCron, setCustomCron] = useState(value || '');

    // Helper to parse existing cron string into state
    useEffect(() => {
        if (isModalOpen && value) {
            parseCron(value);
        }
    }, [isModalOpen, value]);

    const parseCron = (cronStr) => {
        if (!cronStr) return;
        const parts = cronStr.trim().split(/\s+/);
        if (parts.length < 5) {
            setActiveTab('custom');
            setCustomCron(cronStr);
            return;
        }

        const [min, hour, dayOfMonth, month, dayOfWeek] = parts;

        // Check if it's a simple time (no ranges/steps in min/hour)
        const isSimpleTime = /^\d+$/.test(min) && /^\d+$/.test(hour);

        if (!isSimpleTime) {
            setActiveTab('custom');
            setCustomCron(cronStr);
            return;
        }

        // Convert cron time to HH:MM format
        const formattedTime = `${hour.padStart(2, '0')}:${min.padStart(2, '0')}`;
        setTime(formattedTime);

        // Identify type
        if (dayOfMonth === '*' && month === '*' && dayOfWeek === '*') {
            setActiveTab('daily');
        } else if (dayOfMonth === '*' && month === '*' && dayOfWeek !== '*') {
            setActiveTab('weekly');
            // Parse days (handle comma separated)
            const days = dayOfWeek.split(',');
            setSelectedDays(days);
        } else {
            setActiveTab('custom');
            setCustomCron(cronStr);
        }
    };

    const generateCron = () => {
        if (activeTab === 'custom') {
            return customCron;
        }

        const [hour, min] = time.split(':');
        const loadHour = parseInt(hour, 10);
        const loadMin = parseInt(min, 10);

        if (activeTab === 'daily') {
            return `${loadMin} ${loadHour} * * *`;
        }

        if (activeTab === 'weekly') {
            const days = selectedDays.length > 0 ? selectedDays.join(',') : '*';
            return `${loadMin} ${loadHour} * * ${days}`;
        }

        return customCron;
    };

    const handleSave = () => {
        const newCron = generateCron();
        onChange(newCron);
        setIsModalOpen(false);
    };

    const toggleDay = (dayVal) => {
        if (selectedDays.includes(dayVal)) {
            setSelectedDays(selectedDays.filter(d => d !== dayVal));
        } else {
            setSelectedDays([...selectedDays, dayVal]);
        }
    };

    const getSummary = () => {
        if (!value) return 'Not scheduled';
        const parts = value.trim().split(/\s+/);
        if (parts.length < 5) return value;

        const [min, hour, dayOfMonth, month, dayOfWeek] = parts;
        const isSimpleTime = /^\d+$/.test(min) && /^\d+$/.test(hour);

        if (isSimpleTime && dayOfMonth === '*' && month === '*' && dayOfWeek === '*') {
            return `Daily at ${hour.padStart(2, '0')}:${min.padStart(2, '0')}`;
        }

        if (isSimpleTime && dayOfMonth === '*' && month === '*' && dayOfWeek !== '*') {
            const days = dayOfWeek.split(',').map(d => {
                const found = DAYS.find(day => day.value === d);
                return found ? found.label : d;
            }).join(', ');
            return `Weekly on ${days} at ${hour.padStart(2, '0')}:${min.padStart(2, '0')}`;
        }

        return value; // Custom or complex
    };

    return (
        <div style={styles.container}>
            <div style={styles.summaryContainer}>
                <button
                    type="button"
                    style={styles.editButton}
                    onClick={() => setIsModalOpen(true)}
                >
                    Schedule
                </button>
                <div style={styles.summaryText} title={value}>
                    {getSummary()}
                </div>
            </div>

            {isModalOpen && (
                <div style={styles.modalOverlay}>
                    <div style={styles.modalContent}>
                        <h3 style={{ marginTop: 0 }}>Configure Schedule</h3>

                        <div style={styles.tabs}>
                            <div style={styles.tab(activeTab === 'daily')} onClick={() => setActiveTab('daily')}>Daily</div>
                            <div style={styles.tab(activeTab === 'weekly')} onClick={() => setActiveTab('weekly')}>Weekly</div>
                            <div style={styles.tab(activeTab === 'custom')} onClick={() => setActiveTab('custom')}>Custom</div>
                        </div>

                        <div style={{ minHeight: '150px' }}>
                            {activeTab === 'daily' && (
                                <div style={styles.formGroup}>
                                    <label style={styles.label}>Time of Day</label>
                                    <input
                                        type="time"
                                        value={time}
                                        onChange={(e) => setTime(e.target.value)}
                                        style={styles.timeInput}
                                    />
                                    <p style={{ fontSize: '0.8rem', color: '#666', marginTop: '5px' }}>
                                        Trigger the message collection once every day at this time.
                                    </p>
                                </div>
                            )}

                            {activeTab === 'weekly' && (
                                <div>
                                    <div style={styles.formGroup}>
                                        <label style={styles.label}>Time of Day</label>
                                        <input
                                            type="time"
                                            value={time}
                                            onChange={(e) => setTime(e.target.value)}
                                            style={styles.timeInput}
                                        />
                                    </div>
                                    <div style={styles.formGroup}>
                                        <label style={styles.label}>Days of Week</label>
                                        <div style={styles.dayOfWeekContainer}>
                                            {DAYS.map(day => (
                                                <label key={day.value} style={styles.checkboxLabel}>
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedDays.includes(day.value)}
                                                        onChange={() => toggleDay(day.value)}
                                                    />
                                                    {day.label}
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {activeTab === 'custom' && (
                                <div style={styles.formGroup}>
                                    <label style={styles.label}>Cron Expression</label>
                                    <input
                                        type="text"
                                        value={customCron}
                                        onChange={(e) => setCustomCron(e.target.value)}
                                        placeholder="* * * * *"
                                        style={styles.input}
                                    />
                                    <p style={{ fontSize: '0.8rem', color: '#666', marginTop: '5px' }}>
                                        Format: Minute Hour DayOfMonth Month DayOfWeek
                                    </p>
                                </div>
                            )}
                        </div>

                        <div style={styles.footer}>
                            <button
                                type="button"
                                style={styles.cancelButton}
                                onClick={() => setIsModalOpen(false)}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                style={styles.saveButton}
                                onClick={handleSave}
                            >
                                Save
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CronPickerWidget;
