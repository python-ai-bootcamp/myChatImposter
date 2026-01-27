
/**
 * Validates a cron expression.
 * @param {string} cron - The cron expression to validate.
 * @returns {{valid: boolean, error: string|null}} Result object.
 */
export const validateCronExpression = (cron) => {
    if (!cron) return { valid: false, error: 'Required' };
    const parts = cron.trim().split(/\s+/);
    if (parts.length !== 5) {
        return { valid: false, error: 'Must have 5 parts (min hour day month weekday)' };
    }
    const validChars = /^[0-9*/,-]+$/;
    if (!parts.every(p => validChars.test(p))) {
        return { valid: false, error: 'Invalid characters. Allowed: 0-9 * / , -' };
    }
    return { valid: true, error: null };
};
