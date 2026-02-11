import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';
import {
    CustomFieldTemplate, CustomObjectFieldTemplate, CustomCheckboxWidget,
    CustomArrayFieldTemplate, CollapsibleObjectFieldTemplate, InlineObjectFieldTemplate,
    InlineFieldTemplate, NarrowTextWidget, SizedTextWidget,
    NestedCollapsibleObjectFieldTemplate, SystemPromptWidget, InlineCheckboxFieldTemplate,
    TimezoneSelectWidget, LanguageSelectWidget
} from '../components/FormTemplates';
import { GroupTrackingArrayTemplate } from '../components/templates/GroupTrackingArrayTemplate';
import { NullFieldTemplate } from '../components/templates/NullFieldTemplate';
import { GroupNameSelectorWidget } from '../components/widgets/GroupNameSelectorWidget';
import { ReadOnlyTextWidget } from '../components/widgets/ReadOnlyTextWidget';
import { validateCronExpression } from '../utils/validation';
import CronPickerWidget from '../components/CronPickerWidget';
import { FloatingErrorBanner } from '../components/PageLayout';
import '../styles/DarkFormStyles.css';

function RestrictedEditPage() {
    const { botId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const formRef = useRef(null);

    const [schema, setSchema] = useState(null);
    const [formData, setFormData] = useState(null);
    const [error, setError] = useState(null);
    const [availableGroups, setAvailableGroups] = useState([]);
    const [cronErrors, setCronErrors] = useState([]);
    const [validationError, setValidationError] = useState(null);
    const [scrollToErrorTrigger, setScrollToErrorTrigger] = useState(0);

    const handleScrollToError = () => {
        setScrollToErrorTrigger(prev => prev + 1);

        // Robust retry mechanism to find the element after DOM updates
        let attempts = 0;
        const maxAttempts = 10;
        const intervalTime = 100;

        const tryScroll = () => {
            const firstIndex = cronErrors.findIndex(e => e);
            if (firstIndex !== -1) {
                const elementId = `root_features_periodic_group_tracking_tracked_groups_${firstIndex}_cronTrackingSchedule`;
                const element = document.getElementById(elementId);
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    element.focus();
                    return;
                }
            }
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(tryScroll, intervalTime);
            }
        };
        setTimeout(tryScroll, 100);
    };


    const [userStatus, setUserStatus] = useState(null);
    const isNew = location.state?.isNew;
    const isLinked = userStatus === 'connected';

    // Debounced validation
    useEffect(() => {
        const timer = setTimeout(async () => {
            // 1. Cron validation
            const tracking = formData?.features?.periodic_group_tracking?.tracked_groups;
            let newCronErrors = [];
            if (tracking && Array.isArray(tracking)) {
                for (let i = 0; i < tracking.length; i++) {
                    const cron = tracking[i].cronTrackingSchedule;
                    const validation = validateCronExpression(cron);
                    if (!validation.valid) {
                        newCronErrors[i] = validation.error;
                    }
                }
            }
            if (JSON.stringify(newCronErrors) !== JSON.stringify(cronErrors)) {
                setCronErrors(newCronErrors);
            }

            // 2. Backend feature limit validation
            if (formData && botId) {
                try {
                    const response = await fetch(`/api/external/bots/${botId}/validate-config`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ features: formData.features || {} })
                    });
                    if (response.ok) {
                        const result = await response.json();
                        if (!result.valid) {
                            setValidationError(result.error_message);
                        } else {
                            setValidationError(null);
                        }
                    }
                } catch (err) {
                    console.warn('Validation API error:', err);
                }
            }
        }, 300);

        return () => clearTimeout(timer);
    }, [formData, cronErrors, botId]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const schemaResponse = await fetch('/api/external/bots/schema');
                if (!schemaResponse.ok) throw new Error('Failed to fetch form schema.');
                const schemaData = await schemaResponse.json();
                setSchema(schemaData);

                let initialFormData;
                if (isNew) {
                    const defaultsResponse = await fetch('/api/external/bots/defaults');
                    if (!defaultsResponse.ok) throw new Error('Failed to fetch configuration defaults.');
                    initialFormData = await defaultsResponse.json();
                    initialFormData.bot_id = botId;

                    const localTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
                    if (localTimezone && initialFormData.configurations?.user_details) {
                        initialFormData.configurations.user_details.timezone = localTimezone;
                    }

                    try {
                        const languagesResponse = await fetch('/api/external/resources/languages');
                        if (languagesResponse.ok) {
                            const languages = await languagesResponse.json();
                            const browserLang = navigator.language || navigator.userLanguage;
                            if (browserLang) {
                                const baseLang = browserLang.split('-')[0].toLowerCase();
                                const isSupported = languages.some(l => l.code === baseLang);
                                if (isSupported && initialFormData.configurations?.user_details) {
                                    initialFormData.configurations.user_details.language_code = baseLang;
                                }
                            }
                        }
                    } catch (langErr) {
                        console.warn("Failed to auto-detect language:", langErr);
                    }
                } else {
                    const dataResponse = await fetch(`/api/external/bots/${botId}`);
                    if (!dataResponse.ok) throw new Error('Failed to fetch configuration content.');
                    initialFormData = await dataResponse.json();

                    try {
                        const statusRes = await fetch(`/api/external/bots/${botId}/info`);
                        if (statusRes.ok) {
                            const statusData = await statusRes.json();
                            if (statusData.configurations && statusData.configurations.length > 0) {
                                setUserStatus(statusData.configurations[0].status);
                            }
                        }
                    } catch (e) {
                        console.warn("Failed to fetch status:", e);
                    }
                }
                setFormData(initialFormData);
            } catch (err) {
                setError(err.message);
            }
        };

        fetchData();
    }, [botId, isNew]);

    useEffect(() => {
        const fetchGroups = async () => {
            if (userStatus !== 'connected') {
                setAvailableGroups([]);
                return;
            }

            try {
                const groupsRes = await fetch(`/api/external/bots/${botId}/groups`);
                if (groupsRes.ok) {
                    const groupsData = await groupsRes.json();
                    setAvailableGroups(groupsData.groups || []);
                }
            } catch (groupsError) {
                console.warn("Could not fetch groups:", groupsError);
            }
        };

        if (!isNew) {
            fetchGroups();
        }
    }, [botId, isNew, userStatus]);


    const handleFormChange = (e) => {
        const newFormData = e.formData;
        const tracking = newFormData?.features?.periodic_group_tracking?.tracked_groups;
        if (tracking && Array.isArray(tracking) && availableGroups.length > 0) {
            tracking.forEach(item => {
                if (item.groupIdentifier) {
                    const group = availableGroups.find(g => g.id === item.groupIdentifier);
                    if (group && item.displayName !== group.subject) {
                        item.displayName = group.subject;
                    }
                }
            });
        }
        setFormData(newFormData);
    };

    const performSave = async (submittedData) => {
        setCronErrors([]);
        let hasCronErrors = false;
        const newCronErrors = [];
        const tracking = submittedData?.features?.periodic_group_tracking?.tracked_groups;

        if (tracking && Array.isArray(tracking)) {
            for (let i = 0; i < tracking.length; i++) {
                const cron = tracking[i].cronTrackingSchedule;
                const validation = validateCronExpression(cron);
                if (!validation.valid) {
                    newCronErrors[i] = validation.error;
                    hasCronErrors = true;
                }
            }
        }

        if (hasCronErrors) {
            setCronErrors(newCronErrors);
            throw new Error("Validation failed");
        }

        if (!isNew && submittedData.bot_id !== botId) {
            throw new Error("The bot_id cannot be changed.");
        }

        const method = isNew ? 'PUT' : 'PATCH';
        const endpoint = `/api/external/bots/${botId}`;
        const finalApiData = { ...submittedData, bot_id: botId };

        const saveResponse = await fetch(endpoint, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(finalApiData),
        });

        if (!saveResponse.ok) {
            const errorBody = await saveResponse.json();
            const detail = typeof errorBody.detail === 'object' && errorBody.detail !== null
                ? JSON.stringify(errorBody.detail, null, 2)
                : errorBody.detail;
            throw new Error(detail || 'Failed to save configuration.');
        }

        return finalApiData;
    };

    const [savingStatus, setSavingStatus] = useState('idle');

    const handleSaveConfiguration = async () => {
        if (!formRef.current) return;
        setSavingStatus('saving');
        setError(null);
        try {
            actionIntentRef.current = 'save';
            formRef.current.submit();
        } catch (err) {
            setSavingStatus('idle');
        }
    };

    const handleSaveAndLoad = async () => {
        if (!formRef.current) return;
        setSavingStatus('loading');
        setError(null);
        actionIntentRef.current = 'load';
        formRef.current.submit();
    };

    const actionIntentRef = useRef('save');

    const onFormSubmit = async ({ formData: submittedData }) => {
        try {
            await performSave(submittedData);

            if (actionIntentRef.current === 'load') {
                let action = 'link';
                if (userStatus && userStatus !== 'disconnected' && userStatus !== 'error') {
                    action = 'reload';
                }

                const actionRes = await fetch(`/api/external/bots/${botId}/actions/${action}`, {
                    method: 'POST'
                });

                if (!actionRes.ok) {
                    const err = await actionRes.json();
                    throw new Error(`Configuration saved, but failed to ${action}: ${err.detail}`);
                }
            }

            navigate('/operator/dashboard');

        } catch (err) {
            if (err.message !== "Validation failed") {
                setError(`Error: ${err.message}`);
            }
            setSavingStatus('idle');
        }
    };


    const handleCancel = () => {
        navigate('/operator/dashboard');
    };

    if (error) {
        return <div style={{ padding: '20px', color: 'red' }}>{error}</div>;
    }

    if (!schema || !formData) {
        return <div style={{ padding: '20px', color: '#e2e8f0' }}>Loading form...</div>;
    }

    const templates = {
        FieldTemplate: CustomFieldTemplate,
        ObjectFieldTemplate: CustomObjectFieldTemplate,
        ArrayFieldTemplate: CustomArrayFieldTemplate
    };

    const widgets = {
        CheckboxWidget: CustomCheckboxWidget,
        NarrowTextWidget: NarrowTextWidget,
        SizedTextWidget: SizedTextWidget,
        GroupNameSelectorWidget: GroupNameSelectorWidget,
        ReadOnlyTextWidget: ReadOnlyTextWidget,
        CronPickerWidget: CronPickerWidget,
        SystemPromptWidget: SystemPromptWidget,
        TimezoneSelectWidget: TimezoneSelectWidget,
        LanguageSelectWidget: LanguageSelectWidget
    };

    const uiSchema = {
        "ui:classNames": "form-container",
        "ui:title": " ",
        "ui:description": " ",
        bot_id: {
            "ui:FieldTemplate": NullFieldTemplate
        },
        configurations: {
            "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
            "ui:title": "User Profile",
            "ui:description": " ",
            "ui:options": { defaultOpen: true },
            user_details: {
                "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
                "ui:title": "Details",
                "ui:options": { defaultOpen: true },
                timezone: {
                    "ui:widget": "TimezoneSelectWidget"
                },
                language_code: {
                    "ui:widget": "LanguageSelectWidget"
                }
            }
        },
        features: {
            "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
            "ui:title": "Features",
            "ui:options": { defaultOpen: true },
            automatic_bot_reply: {
                "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
                "ui:title": "Automatic Bot Reply",
                enabled: {
                    "ui:FieldTemplate": InlineCheckboxFieldTemplate
                },
                respond_to_whitelist: { "ui:title": " " },
                respond_to_whitelist_group: { "ui:title": " " },
                chat_system_prompt: {
                    "ui:widget": "textarea",
                    "ui:options": { rows: 5 }
                }
            },
            periodic_group_tracking: {
                "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
                "ui:title": "Periodic Group Tracking",
                enabled: {
                    "ui:FieldTemplate": InlineCheckboxFieldTemplate
                },
                tracked_groups: {
                    "ui:title": " ",
                    "ui:ArrayFieldTemplate": GroupTrackingArrayTemplate,
                    items: {
                        "ui:ObjectFieldTemplate": InlineObjectFieldTemplate,
                        "ui:order": ["displayName", "groupIdentifier", "cronTrackingSchedule"],
                        displayName: {
                            "ui:FieldTemplate": InlineFieldTemplate,
                            "ui:title": "Name",
                            "ui:widget": "GroupNameSelectorWidget"
                        },
                        groupIdentifier: {
                            "ui:FieldTemplate": InlineFieldTemplate,
                            "ui:title": "ID",
                            "ui:widget": "ReadOnlyTextWidget"
                        },
                        cronTrackingSchedule: {
                            "ui:FieldTemplate": InlineFieldTemplate,
                            "ui:title": " ",
                            "ui:widget": "CronPickerWidget",
                            "ui:options": { width: "100%" },
                            "ui:placeholder": "0/15 * * * *"
                        }
                    }
                }
            },
            kid_phone_safety_tracking: {
                "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
                "ui:title": "Kid Phone Safety Tracking",
                enabled: {
                    "ui:FieldTemplate": InlineCheckboxFieldTemplate
                }
            }
        }
    };

    return (
        <div className="profile-page">
            <style>{`
                .profile-page {
                    height: calc(100vh - 60px);
                    width: 100vw;
                    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                    color: #e2e8f0;
                    font-family: 'Inter', sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    padding: 2rem;
                    position: relative;
                    overflow: hidden; /* Prevent external scroll */
                    box-sizing: border-box;
                }

                .profile-container {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(20px);
                    padding: 2rem;
                    border-radius: 1.5rem;
                    width: 100%;
                    max-width: 1000px;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                    z-index: 10;
                    display: flex;
                    flex-direction: column;
                    height: 100%;
                    max-height: 100%;
                    overflow: hidden;
                }

                .profile-header {
                    margin-bottom: 1.5rem;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    padding-bottom: 1rem;
                    flex-shrink: 0;
                }

                .form-content {
                    flex: 1;
                    overflow-y: auto;
                    min-height: 0;
                    padding-right: 10px;
                    scrollbar-width: thin;
                    scrollbar-color: rgba(255,255,255,0.2) transparent;
                }
                .form-content::-webkit-scrollbar {
                    width: 6px;
                }
                .form-content::-webkit-scrollbar-thumb {
                    background-color: rgba(255,255,255,0.2);
                    border-radius: 3px;
                }

                .profile-header h1 {
                    font-size: 2rem;
                    font-weight: 800;
                    margin-bottom: 0.5rem;
                    background: linear-gradient(to right, #c084fc, #6366f1);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }

                /* Background shapes */
                .shape {
                    position: absolute;
                    filter: blur(100px);
                    z-index: 0;
                    opacity: 0.4;
                    pointer-events: none;
                }
                .shape-1 {
                    top: -20%;
                    left: -20%;
                    width: 60vw;
                    height: 60vw;
                    background: radial-gradient(circle, #4f46e5 0%, transparent 70%);
                }
                .shape-2 {
                    bottom: -20%;
                    right: -20%;
                    width: 50vw;
                    height: 50vw;
                    background: radial-gradient(circle, #ec4899 0%, transparent 70%);
                }

                /* Action Bar Styling */
                .action-bar {
                    margin-top: 1rem;
                    display: flex;
                    gap: 1rem;
                    justify-content: flex-end;
                    border-top: 1px solid rgba(255, 255, 255, 0.1);
                    padding-top: 1rem;
                    flex-shrink: 0;
                }

                .btn-glass {
                    padding: 0.75rem 1.5rem;
                    border-radius: 0.75rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }

                .btn-primary-glass {
                    background: linear-gradient(135deg, #6366f1, #8b5cf6);
                    color: white;
                    border: none;
                    box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.3);
                }
                .btn-primary-glass:hover:not(:disabled) {
                    transform: translateY(-2px);
                    box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4);
                }

                .btn-success-glass {
                    background: linear-gradient(135deg, #22c55e, #16a34a);
                    color: white;
                    border: none;
                    box-shadow: 0 4px 6px -1px rgba(34, 197, 94, 0.3);
                }
                .btn-success-glass:hover:not(:disabled) {
                    transform: translateY(-2px);
                    box-shadow: 0 10px 15px -3px rgba(34, 197, 94, 0.4);
                }

                .btn-secondary-glass {
                    background: rgba(30, 41, 59, 0.6);
                    color: #e2e8f0;
                }
                .btn-secondary-glass:hover:not(:disabled) {
                    background: rgba(30, 41, 59, 0.8);
                }

                .btn-glass:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                    transform: none !important;
                }
            `}</style>

            <div className="shape shape-1" />
            <div className="shape shape-2" />

            <FloatingErrorBanner isVisible={validationError || cronErrors.some(e => e)} darkMode={true}>
                <strong>⚠️ Cannot Save:</strong>
                {validationError ? (
                    <>
                        <span style={{ marginLeft: '5px' }}>{validationError}</span>
                        <button
                            type="button"
                            onClick={() => document.getElementById('root_features')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                            style={{ marginLeft: '10px', padding: '4px 8px', fontSize: '12px', cursor: 'pointer', textDecoration: 'underline', background: 'none', border: 'none', color: '#991b1b', fontWeight: 'bold' }}
                        >
                            Go to Features
                        </button>
                    </>
                ) : (
                    <span
                        onClick={handleScrollToError}
                        style={{ marginLeft: '5px', textDecoration: 'underline', cursor: 'pointer', fontWeight: 'bold' }}
                        title="Click to locate the error"
                    >
                        Invalid cron expression in tracked groups.
                    </span>
                )}
            </FloatingErrorBanner>

            <div className="profile-container">
                <div className="profile-header">
                    <h1>{isNew ? 'New Configuration' : `Edit Bot: ${botId}`}</h1>
                </div>

                <div className="form-content">
                    <Form
                        className="dark-form"
                        ref={formRef}
                        schema={schema}
                        uiSchema={uiSchema}
                        formData={formData}
                        validator={validator}
                        onSubmit={onFormSubmit}
                        onChange={handleFormChange}
                        onError={(errors) => {
                            console.log('Form errors:', errors);
                            setSavingStatus('idle');
                        }}
                        disabled={savingStatus !== 'idle'}
                        templates={templates}
                        widgets={widgets}
                        formContext={{
                            availableGroups,
                            isLinked: isLinked,
                            formData,
                            setFormData,
                            cronErrors,
                            saveAttempt: 0,
                            scrollToErrorTrigger
                        }}
                    >
                        <div />
                    </Form>
                </div>

                <div className="action-bar">
                    <button
                        type="button"
                        className="btn-glass btn-secondary-glass"
                        onClick={handleCancel}
                        disabled={savingStatus !== 'idle'}
                    >
                        Cancel
                    </button>

                    <button
                        type="button"
                        className="btn-glass btn-success-glass"
                        onClick={handleSaveAndLoad}
                        disabled={savingStatus !== 'idle' || cronErrors.some(e => e) || validationError}
                        title="Save and instantly reload the bot"
                    >
                        {savingStatus === 'loading' ? 'Processing...' : 'Save & Reload'}
                    </button>

                    <button
                        type="button"
                        className="btn-glass btn-primary-glass"
                        onClick={handleSaveConfiguration}
                        disabled={savingStatus !== 'idle' || cronErrors.some(e => e) || validationError}
                        title="Save configuration only"
                    >
                        {savingStatus === 'saving' ? 'Saving...' : 'Save Configuration'}
                    </button>
                </div>
            </div>
        </div>
    );
}

export default RestrictedEditPage;
