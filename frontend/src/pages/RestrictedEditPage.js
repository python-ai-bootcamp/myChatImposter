import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';
import {
    CustomFieldTemplate, CustomObjectFieldTemplate, CustomCheckboxWidget,
    CustomArrayFieldTemplate, CollapsibleObjectFieldTemplate, InlineObjectFieldTemplate,
    InlineFieldTemplate, NarrowTextWidget, SizedTextWidget,
    NestedCollapsibleObjectFieldTemplate, SystemPromptWidget, InlineCheckboxFieldTemplate,
    FlatProviderConfigTemplate, TimezoneSelectWidget, LanguageSelectWidget
} from '../components/FormTemplates';
import { GroupTrackingArrayTemplate } from '../components/templates/GroupTrackingArrayTemplate';
import { NullFieldTemplate } from '../components/templates/NullFieldTemplate';
import { GroupNameSelectorWidget } from '../components/widgets/GroupNameSelectorWidget';
import { ReadOnlyTextWidget } from '../components/widgets/ReadOnlyTextWidget';
import { validateCronExpression } from '../utils/validation';
import CronPickerWidget from '../components/CronPickerWidget';
import { PageContainer, ContentCard, ScrollablePanel, FixedFooter } from '../components/PageLayout';

function RestrictedEditPage() {
    const { userId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const formRef = useRef(null);

    const [schema, setSchema] = useState(null);
    const [formData, setFormData] = useState(null);
    const [error, setError] = useState(null);
    const [isSaving, setIsSaving] = useState(false);
    const [availableGroups, setAvailableGroups] = useState([]);
    const [cronErrors, setCronErrors] = useState([]);

    const [userStatus, setUserStatus] = useState(null);

    // isNew determines if we are creating a new user (PUT) or editing (PATCH)
    const isNew = location.state?.isNew;

    // Scheduled check for cron errors (polling/debounced)
    useEffect(() => {
        const timer = setTimeout(() => {
            const tracking = formData?.features?.periodic_group_tracking?.tracked_groups;
            if (tracking && Array.isArray(tracking)) {
                const newCronErrors = [];

                for (let i = 0; i < tracking.length; i++) {
                    const cron = tracking[i].cronTrackingSchedule;
                    const validation = validateCronExpression(cron);
                    if (!validation.valid) {
                        newCronErrors[i] = validation.error;
                    }
                }

                if (JSON.stringify(newCronErrors) !== JSON.stringify(cronErrors)) {
                    setCronErrors(newCronErrors);
                }
            } else {
                if (cronErrors.length > 0) setCronErrors([]);
            }
        }, 1000);

        return () => clearTimeout(timer);
    }, [formData, cronErrors]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch Schema from UI API
                const schemaResponse = await fetch('/api/external/ui/users/schema');
                if (!schemaResponse.ok) throw new Error('Failed to fetch form schema.');
                const schemaData = await schemaResponse.json();
                setSchema(schemaData);

                let initialFormData;
                if (isNew) {
                    initialFormData = {
                        user_id: userId,
                        configurations: {
                            user_details: {
                                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
                                language_code: "en"
                            }
                        },
                        features: {}
                    };

                    // Use browser's detected language if supported
                    try {
                        const languagesResponse = await fetch('/api/external/resources/languages');
                        if (languagesResponse.ok) {
                            const languages = await languagesResponse.json();
                            const browserLang = navigator.language || navigator.userLanguage;
                            if (browserLang) {
                                const baseLang = browserLang.split('-')[0].toLowerCase();
                                const isSupported = languages.some(l => l.code === baseLang);
                                if (isSupported) {
                                    initialFormData.configurations.user_details.language_code = baseLang;
                                }
                            }
                        }
                    } catch (langErr) {
                        console.warn("Failed to auto-detect language:", langErr);
                    }
                } else {
                    // Fetch User Data from UI API
                    const dataResponse = await fetch(`/api/external/ui/users/${userId}`);
                    if (!dataResponse.ok) throw new Error('Failed to fetch configuration content.');
                    initialFormData = await dataResponse.json();

                    // Fetch Status for Button Logic
                    try {
                        const statusRes = await fetch(`/api/external/users/${userId}/info`);
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
    }, [userId, isNew]);

    // Fetch Groups (Requires owner permissions)
    useEffect(() => {
        const fetchGroups = async () => {
            try {
                const groupsRes = await fetch(`/api/external/users/${userId}/groups`);
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
    }, [userId, isNew]);


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

        // 2. Validate User ID
        if (!isNew && submittedData.user_id !== userId) {
            throw new Error("The user_id cannot be changed.");
        }

        // 3. Save Configuration
        const method = isNew ? 'PUT' : 'PATCH';
        const endpoint = `/api/external/ui/users/${userId}`;
        const finalApiData = { ...submittedData, user_id: userId };

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

    const handleSaveConfiguration = async () => {
        if (!formRef.current) return;
        setIsSaving(true);
        setError(null);
        try {
            // Trigger RJSF validation by creating a synthetic submit
            // Accessing internal RJSF state/methods to get current data is tricky without a submit event.
            // But we can trigger the form submit, and handle the logic in the onSubmit callback.
            // Problem: We need to distinguish WHICH button halted the submit.
            // Solution: We'll set a ref or state indicating the intent, then submit.
            setActionIntent('save');
            formRef.current.submit();
        } catch (err) {
            // Basic errors caught here
        }
        // finally block handled in onSubmit
    };

    const handleSaveAndLoad = async () => {
        if (!formRef.current) return;
        setIsSaving(true);
        setError(null);
        setActionIntent('load');
        formRef.current.submit();
    };

    const [actionIntent, setActionIntent] = useState('save'); // 'save' or 'load'

    const onFormSubmit = async ({ formData: submittedData }) => {
        try {
            await performSave(submittedData);

            if (actionIntent === 'load') {
                // Perform Link or Reload based on status
                let action = 'link';
                if (userStatus && userStatus !== 'disconnected' && userStatus !== 'error') {
                    action = 'reload';
                }

                const actionRes = await fetch(`/api/external/users/${userId}/actions/${action}`, {
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
            setIsSaving(false);
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
        user_id: {
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
            <PageContainer>
                <ContentCard title={isNew ? 'New Configuration: ' + userId : `Edit Configuration: ${userId}`} maxWidth="1000px">
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
                                setIsSaving(false);
                            }}
                            disabled={isSaving}
                            templates={templates}
                            widgets={widgets}
                            formContext={{
                                availableGroups,
                                isLinked: false,
                                formData,
                                setFormData,
                                cronErrors,
                                saveAttempt: 0
                            }}
                        >
                            <div />
                        </Form>
                    </ScrollablePanel>
                </ContentCard>
            </PageContainer>
            <FixedFooter>
                <div>
                    <button
                        type="button"
                        onClick={handleSaveConfiguration}
                        disabled={isSaving}
                        title="saves new configuration without reloading the bot (new changes will take effect next time the bt is reloaded)"
                        style={{ marginRight: '10px', padding: '10px 20px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        {isSaving && actionIntent === 'save' ? 'Saving...' : 'Save Configuration'}
                    </button>

                    <button
                        type="button"
                        onClick={handleSaveAndLoad}
                        disabled={isSaving}
                        title="reloads the bot with the new configuration saved"
                        style={{ marginRight: '10px', padding: '10px 20px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        {isSaving && actionIntent === 'load' ? 'Processing...' : 'Save & Load'}
                    </button>

                    <button
                        type="button"
                        onClick={handleCancel}
                        disabled={isSaving}
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
