import React, { useEffect, useState, useLayoutEffect } from 'react';
import ReactDOM from 'react-dom';

const SelectMenuPortal = ({ children, anchorRef, isOpen, onClose, className }) => {
    const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
    const menuRef = React.useRef(null);

    useLayoutEffect(() => {
        if (isOpen && anchorRef.current) {
            const updatePosition = () => {
                const rect = anchorRef.current.getBoundingClientRect();
                const scrollTop = window.scrollY || document.documentElement.scrollTop;
                const scrollLeft = window.scrollX || document.documentElement.scrollLeft;

                setPosition({
                    top: rect.bottom + scrollTop + 4, // 4px gap
                    left: rect.left + scrollLeft,
                    width: rect.width
                });
            };

            updatePosition();

            // Re-calculate on resize/scroll
            window.addEventListener('resize', updatePosition);
            window.addEventListener('scroll', updatePosition, true); // Capture to detect specific scrolling containers

            return () => {
                window.removeEventListener('resize', updatePosition);
                window.removeEventListener('scroll', updatePosition, true);
            };
        }
    }, [isOpen, anchorRef]);

    // Handle click outside
    useEffect(() => {
        if (!isOpen) return;

        const handleClickOutside = (event) => {
            // Check if click is inside the anchor (toggle button) or the menu
            if (
                anchorRef.current &&
                anchorRef.current.contains(event.target)
            ) {
                // If clicked on anchor, let the anchor handle the toggle
                return;
            }

            if (
                menuRef.current &&
                !menuRef.current.contains(event.target)
            ) {
                if (onClose) onClose();
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        // Also handle touch for mobile
        document.addEventListener('touchstart', handleClickOutside);

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('touchstart', handleClickOutside);
        };
    }, [isOpen, anchorRef, onClose]);

    if (!isOpen) return null;

    return ReactDOM.createPortal(
        <div
            ref={menuRef}
            className={className}
            style={{
                position: 'absolute',
                top: position.top,
                left: position.left,
                width: position.width,
                zIndex: 99999, // Ensure it floats above everything
            }}
        >
            {children}
        </div>,
        document.body
    );
};

export default SelectMenuPortal;
