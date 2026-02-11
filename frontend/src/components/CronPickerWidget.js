import React, { useState, useEffect } from 'react';

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
        backgroundColor: 'rgba(15, 23, 42, 0.6)', // Dark background
        border: '1px solid rgba(255, 255, 255, 0.15)',
        borderRadius: '4px',
        minWidth: '150px',
        fontSize: '0.8rem',
        lineHeight: '1.2',
        color: '#f8fafc', // Light text
    },
    editButton: {
        padding: '2px 8px',
        backgroundColor: '#6366f1', // Indigo-500
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
        backgroundColor: 'rgba(0,0,0,0.7)', // Darker overlay
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
    },
    modalContent: {
        backgroundColor: '#1e293b', // Slate-800
        color: '#f8fafc',
        padding: '20px',
        borderRadius: '8px',
        width: '400px',
        boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
    },
    tabs: {
        display: 'flex',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        marginBottom: '20px',
    },
    tab: (isActive) => ({
        padding: '10px 15px',
        cursor: 'pointer',
        borderBottom: isActive ? '2px solid #818cf8' : 'none',
        color: isActive ? '#818cf8' : '#94a3b8',
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
        color: '#e2e8f0',
    },
    input: {
        padding: '8px',
        border: '1px solid rgba(255, 255, 255, 0.2)',
        borderRadius: '4px',
        width: '100%',
        boxSizing: 'border-box',
        backgroundColor: 'rgba(15, 23, 42, 0.6)',
        color: '#f8fafc',
    },
    timeInput: {
        padding: '8px',
        border: '1px solid rgba(255, 255, 255, 0.2)',
        borderRadius: '4px',
        width: '120px',
        backgroundColor: 'rgba(15, 23, 42, 0.6)',
        color: '#f8fafc',
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
        color: '#e2e8f0',
    },
    footer: {
        display: 'flex',
        justifyContent: 'flex-end',
        gap: '10px',
        marginTop: '20px',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        paddingTop: '15px',
    },
    cancelButton: {
        padding: '8px 16px',
        backgroundColor: 'transparent',
        color: '#fca5a5',
        border: '1px solid #ef4444',
        borderRadius: '4px',
        cursor: 'pointer',
        fontWeight: '500',
    },
    saveButton: {
        padding: '8px 16px',
        backgroundColor: '#6366f1',
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
    const { value, onChange } = props;
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [activeTab, setActiveTab] = useState('daily'); // daily, weekly, custom

    // State for builder
    const [time, setTime] = useState('20:00');
    const [selectedDays, setSelectedDays] = useState(['1']); // Default Monday
    const [customCron, setCustomCron] = useState(value || '');

    const generateCron = React.useCallback(() => {
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
    }, [activeTab, customCron, time, selectedDays]);

    // Helper to parse existing cron string into state
    const hasParsedRef = React.useRef(false);
    useEffect(() => {
        if (isModalOpen && value) {
            if (!hasParsedRef.current) {
                parseCron(value);
                hasParsedRef.current = true;
            }
        } else {
            hasParsedRef.current = false;
        }
    }, [isModalOpen, value]);

    // Keep custom cron updated when other tabs change
    useEffect(() => {
        if (activeTab !== 'custom') {
            const generated = generateCron();
            setCustomCron(generated);
        }
    }, [activeTab, time, selectedDays, generateCron]);

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
            // Strict validation for weekly: ensure all parts are valid digits 0-6
            const days = dayOfWeek.split(',');
            const allDaysValid = days.every(d => /^[0-6]$/.test(d));

            if (allDaysValid) {
                setActiveTab('weekly');
                setSelectedDays(days);
            } else {
                // If corrupted days, fallback to custom
                setActiveTab('custom');
                setCustomCron(cronStr);
            }
        } else {
            setActiveTab('custom');
            setCustomCron(cronStr);
        }
    };



    const handleCustomChange = (e) => {
        const newCron = e.target.value;
        setCustomCron(newCron);

        // Best-effort reverse sync
        // Only try if it looks like a valid 5-part cron
        const parts = newCron.trim().split(/\s+/);
        if (parts.length === 5) {
            const [min, hour, dayOfMonth, month, dayOfWeek] = parts;
            const isSimpleTime = /^\d+$/.test(min) && /^\d+$/.test(hour);

            if (isSimpleTime) {
                // Formatting time for input type="time"
                const formattedTime = `${hour.padStart(2, '0')}:${min.padStart(2, '0')}`;
                setTime(formattedTime);

                if (dayOfMonth === '*' && month === '*') {
                    if (dayOfWeek === '*') {
                        // Could be daily
                    } else {
                        // Could be weekly - parse days
                        const days = dayOfWeek.split(',');
                        // Only update if valid days
                        const allValid = days.every(d => /^[0-6]$/.test(d));
                        if (allValid) setSelectedDays(days);
                    }
                }
            }
        }
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
        <div style={styles.container} id={props.id} tabIndex="-1">
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
                                        onChange={handleCustomChange}
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
