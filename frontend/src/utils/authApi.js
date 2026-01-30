/**
 * Authentication API client.
 *
 * Handles login and logout operations.
 */

/**
 * Login user with credentials.
 *
 * @param {string} userId - User identifier
 * @param {string} password - User password
 * @returns {Promise<Object>} Login response { success, message, user_id, role, session_id }
 * @throws {Error} If login fails
 */
export const login = async (userId, password) => {
  try {
    const response = await fetch('/api/external/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Include cookies
      body: JSON.stringify({
        user_id: userId,
        password: password,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      // Handle specific error codes
      if (response.status === 429) {
        throw new Error(
          `Too many login attempts. Please try again in ${data.retry_after || '60'} seconds.`
        );
      }
      if (response.status === 423) {
        throw new Error(
          `Account is temporarily locked. Please try again later.`
        );
      }
      throw new Error(data.detail || data.message || 'Login failed');
    }

    return data;
  } catch (error) {
    if (error.message) {
      throw error;
    }
    throw new Error('Network error: Could not connect to server');
  }
};

/**
 * Logout current user.
 *
 * @returns {Promise<Object>} Logout response { success, message }
 */
export const logout = async () => {
  try {
    const response = await fetch('/api/external/auth/logout', {
      method: 'POST',
      credentials: 'include', // Include cookies
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.message || 'Logout failed');
    }

    return data;
  } catch (error) {
    if (error.message) {
      throw error;
    }
    throw new Error('Network error: Could not connect to server');
  }
};
