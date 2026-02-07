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
import { PageContainer, ContentCard, ScrollablePanel, FixedFooter, FloatingErrorBanner } from '../components/PageLayout';

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

        // Robust retry mechanism to find the element after DOM updates (e.g. expansion)
        let attempts = 0;
        const maxAttempts = 10;
        const intervalTime = 100; // Total wait up to 1000ms

        const tryScroll = () => {
            const firstIndex = cronErrors.findIndex(e => e);
            if (firstIndex !== -1) {
                const elementId = `root_features_periodic_group_tracking_tracked_groups_${firstIndex}_cronTrackingSchedule`;
                const element = document.getElementById(elementId);
                if (element) {
                    // Found it! Scroll and focus.
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    element.focus();
                    return;
                }
            }

            // Not found yet, retry?
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(tryScroll, intervalTime);
            }
        };

        // Start trying
        setTimeout(tryScroll, 100); // Initial small delay to let React start rendering
    };


    const [userStatus, setUserStatus] = useState(null);

    // isNew determines if we are creating a new user (PUT) or editing (PATCH)
    const isNew = location.state?.isNew;
    const isLinked = userStatus === 'connected';

    // Debounced validation (cron + backend API)
    useEffect(() => {
        const timer = setTimeout(async () => {
            // 1. Cron validation (local)
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

            // 2. Backend feature limit validation (only if no cron errors)
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
                // Fetch Schema from standard API
                const schemaResponse = await fetch('/api/external/bots/schema');
                if (!schemaResponse.ok) throw new Error('Failed to fetch form schema.');
                const schemaData = await schemaResponse.json();
                setSchema(schemaData);

                let initialFormData;
                if (isNew) {
                    // Fetch dynamic defaults from backend (Single Source of Truth)
                    // The backend now filters this based on X-User-Role (injected by Proxy)
                    const defaultsResponse = await fetch('/api/external/bots/defaults');
                    if (!defaultsResponse.ok) throw new Error('Failed to fetch configuration defaults.');
                    initialFormData = await defaultsResponse.json();

                    // Override with current context
                    initialFormData.bot_id = botId;

                    // Use browser's detected timezone
                    const localTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
                    if (localTimezone && initialFormData.configurations?.user_details) {
                        initialFormData.configurations.user_details.timezone = localTimezone;
                    }

                    // Use browser's detected language if supported
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
                    // Fetch User Data from standard API
                    const dataResponse = await fetch(`/api/external/bots/${botId}`);
                    if (!dataResponse.ok) throw new Error('Failed to fetch configuration content.');
                    initialFormData = await dataResponse.json();

                    // Fetch Status for Button Logic
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

    // Fetch Groups (Requires connected status)
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

        // Auto-populate displayName when groupIdentifier is selected
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

    // Generic Internal Save Function
    const performSave = async (submittedData) => {
        // 1. Validate Cron Expressions
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

        // 2. Validate Bot ID
        if (!isNew && submittedData.bot_id !== botId) {
            throw new Error("The bot_id cannot be changed.");
        }

        // 3. Save Configuration
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

    const [savingStatus, setSavingStatus] = useState('idle'); // 'idle', 'saving', 'loading'

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

    const actionIntentRef = useRef('save'); // 'save' or 'load'

    const onFormSubmit = async ({ formData: submittedData }) => {
        try {
            await performSave(submittedData);

            if (actionIntentRef.current === 'load') {
                // Perform Link or Reload based on status
                let action = 'link';
                if (userStatus && userStatus !== 'disconnected' && userStatus !== 'error') {
                    action = 'reload';
                }

                const actionRes = await fetch(`/api/external/bots/${botId}/actions/${action}`, {
                    method: 'POST'
                });

                if (!actionRes.ok) {
                    // Optimization: If link/reload fails, we warn but don't fail the "Save" part completely?
                    // User probably wants to know.
                    const err = await actionRes.json();
                    throw new Error(`Configuration saved, but failed to ${action}: ${err.detail}`);
                }
            }

            navigate('/');

        } catch (err) {
            if (err.message !== "Validation failed") {
                setError(`Error: ${err.message}`);
            }
            setSavingStatus('idle');
        }
    };


    const handleCancel = () => {
        navigate('/');
    };

    if (error) {
        return <div style={{ padding: '20px', color: 'red' }}>{error}</div>;
    }

    if (!schema || !formData) {
        return <div style={{ padding: '20px' }}>Loading form...</div>;
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
        "ui:description": " ", // Remove restricted text
        bot_id: {
            "ui:FieldTemplate": NullFieldTemplate
        },
        // General Configurations section
        configurations: {
            "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
            "ui:title": "User Profile",
            "ui:description": " ", // Remove restricted text
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
        // Feature Configurations section
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
                respond_to_whitelist: {
                    "ui:title": " "
                },
                respond_to_whitelist_group: {
                    "ui:title": " "
                },
                chat_system_prompt: {
                    "ui:widget": "textarea",
                    "ui:options": {
                        rows: 5
                    }
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
        <>
            <FloatingErrorBanner isVisible={validationError || cronErrors.some(e => e)}>
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

            <PageContainer>
                <ContentCard title={isNew ? 'New Configuration: ' + botId : `Edit Configuration: ${botId}`} maxWidth="1000px">
                    <ScrollablePanel>
                        <Form
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
                    </ScrollablePanel>
                </ContentCard>
            </PageContainer >
            <FixedFooter>
                <div>
                    <button
                        type="button"
                        onClick={handleSaveConfiguration}
                        disabled={savingStatus !== 'idle' || cronErrors.some(e => e) || validationError}
                        title={validationError || (cronErrors.some(e => e) ? 'Fix cron expression errors first' : 'Saves new configuration without reloading the bot')}
                        style={{ marginRight: '10px', padding: '10px 20px', backgroundColor: (cronErrors.some(e => e) || validationError) ? '#6c757d' : '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: (cronErrors.some(e => e) || validationError) ? 'not-allowed' : 'pointer' }}
                    >
                        {savingStatus === 'saving' ? 'Saving...' : 'Save Configuration'}
                    </button>

                    <button
                        type="button"
                        onClick={handleSaveAndLoad}
                        disabled={savingStatus !== 'idle' || cronErrors.some(e => e) || validationError}
                        title={validationError || (cronErrors.some(e => e) ? 'Fix cron expression errors first' : 'Reloads the bot with the new configuration saved')}
                        style={{ marginRight: '10px', padding: '10px 20px', backgroundColor: (cronErrors.some(e => e) || validationError) ? '#6c757d' : '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: (cronErrors.some(e => e) || validationError) ? 'not-allowed' : 'pointer' }}
                    >
                        {savingStatus === 'loading' ? 'Processing...' : 'Save & Load'}
                    </button>

                    <button
                        type="button"
                        onClick={handleCancel}
                        disabled={savingStatus !== 'idle'}
                        style={{ padding: '10px 20px', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        Cancel
                    </button>
                </div>
            </FixedFooter>
        </>
    );
}

export default RestrictedEditPage;
