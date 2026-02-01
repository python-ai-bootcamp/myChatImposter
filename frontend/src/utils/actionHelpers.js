/**
 * Determines if a specific action is enabled based on user status.
 * @param {string} action - The action type ('link', 'unlink', 'edit', 'delete').
 * @param {string} status - The current status of the user (e.g., 'connected', 'disconnected').
 * @param {string|null} selectedUserId - The currently selected user ID.
 * @returns {boolean} - Whether the action is enabled.
 */
export function isActionEnabled(action, status, selectedUserId) {
    if (!selectedUserId) {
        return false; // No user selected, all actions disabled
    }

    const normalizedStatus = status?.toLowerCase() || 'disconnected';

    switch (action) {
        case 'link':
            // Link is enabled only when the user is not connected
            return ['disconnected', 'close', 'error', 'initializing', 'waiting', 'got qr code'].includes(normalizedStatus);
        case 'unlink':
            // Unlink is enabled only when connected
            return normalizedStatus === 'connected';
        case 'edit':
        case 'delete':
            // Edit and Delete are always enabled if a user is selected
            return true;
        default:
            return false;
    }
}
