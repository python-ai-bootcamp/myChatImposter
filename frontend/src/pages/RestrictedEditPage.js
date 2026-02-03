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
                    // For new users, we start with a blank slate or minimal defaults
                    // We can't fetch defaults from admin API.
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
                } else {
                    // Fetch User Data from UI API
                    const dataResponse = await fetch(`/api/external/ui/users/${userId}`);
                    if (!dataResponse.ok) throw new Error('Failed to fetch configuration content.');
                    initialFormData = await dataResponse.json();
                }
                setFormData(initialFormData);
            } catch (err) {
                setError(err.message);
            }
        };

        fetchData();
    }, [userId, isNew]);

    // Fetch Groups (Requires owner permissions, verify this endpoint works for owners)
    useEffect(() => {
        const fetchGroups = async () => {
            try {
                // Groups endpoint is likely still admin-centric or needs verification?
                // Wait, the new gateway logic allows GET /users/{id}/* if owned.
                // /api/external/users/{userId}/groups should work if the gateway regex allows it.
                // Regex: r"/api/external/users/(?P<user_id>[^/]+)" includes /groups!
                // So this should work for the owner.
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

    const handleSave = async ({ formData: submittedData }) => {
        setIsSaving(true);
        setError(null);
        try {
            const currentData = submittedData;

            // 1. Validate Cron Expressions
            setCronErrors([]);
            let hasCronErrors = false;
            const newCronErrors = [];
            const tracking = currentData?.features?.periodic_group_tracking?.tracked_groups;

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
                setIsSaving(false);
                return;
            }

            // 2. Validate User ID
            if (!isNew && currentData.user_id !== userId) {
                throw new Error("The user_id cannot be changed.");
            }

            // 3. Save Configuration
            // PUT for New, PATCH for Existing
            const method = isNew ? 'PUT' : 'PATCH';
            const endpoint = `/api/external/ui/users/${userId}`;
            const finalApiData = { ...currentData, user_id: userId };

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

            navigate('/');

        } catch (err) {
            setError(`Failed to save: ${err.message}`);
        } finally {
            setIsSaving(false);
        }
    };

    const handleCancel = () => {
        navigate('/');
    };

    if (error) {
        return <div style={{ padding: '20px', color: 'red' }}>Error: {error}</div>;
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
        user_id: {
            "ui:FieldTemplate": NullFieldTemplate
        },
        // General Configurations section
        configurations: {
            "ui:ObjectFieldTemplate": CollapsibleObjectFieldTemplate,
            "ui:title": "User Profile",
            user_details: {
                "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
                "ui:title": "Details",
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

    const panelStyle = {
        border: '1px solid #ccc',
        borderRadius: '4px',
        padding: '1rem',
        backgroundColor: '#fff',
        boxSizing: 'border-box'
    };

    const innerPanelStyle = {
        ...panelStyle,
        backgroundColor: '#f9f9f9',
    };

    return (
        <>
            <div style={{ padding: '20px', paddingBottom: '80px' }}>
                <div style={{ maxWidth: '900px', margin: '0 auto' }}>
                    <div style={panelStyle}>
                        <h2>{isNew ? 'New Configuration' : `Edit Configuration`}: {userId}</h2>
                        <div style={{ marginTop: '1rem', minHeight: '60vh' }}>
                            <div style={{ ...innerPanelStyle }}>
                                <Form
                                    ref={formRef}
                                    schema={schema}
                                    uiSchema={uiSchema}
                                    formData={formData}
                                    validator={validator}
                                    onSubmit={handleSave}
                                    onChange={handleFormChange}
                                    onError={(errors) => console.log('Form errors:', errors)}
                                    disabled={isSaving}
                                    templates={templates}
                                    widgets={widgets}
                                    formContext={{
                                        availableGroups,
                                        isLinked: false, // Simpler page, no linking logic here
                                        formData,
                                        setFormData,
                                        cronErrors,
                                        saveAttempt: 0
                                    }}
                                >
                                    <div />
                                </Form>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div style={{
                position: 'fixed',
                bottom: 0,
                left: 0,
                right: 0,
                padding: '1rem',
                backgroundColor: '#f0f0f0',
                borderTop: '1px solid #ccc',
                textAlign: 'center'
            }}>
                <div>
                    <button type="button" onClick={() => formRef.current.submit()} disabled={isSaving} style={{ marginRight: '10px', padding: '10px 20px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px' }}>
                        {isSaving ? 'Saving...' : 'Save Configuration'}
                    </button>
                    <button type="button" onClick={handleCancel} style={{ padding: '10px 20px', border: '1px solid #ccc', borderRadius: '4px' }}>
                        Cancel
                    </button>
                </div>
            </div>
        </>
    );
}

export default RestrictedEditPage;
