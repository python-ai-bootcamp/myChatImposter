import React from 'react';

export const AdvisorIcon = ({ width = "1em", height = "1em", style = {} }) => (
    <svg width={width} height={height} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ verticalAlign: 'middle', ...style }}>
        <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM20 16H6L4 18V4H20V16Z"
            stroke="url(#advisorGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="url(#advisorFill)" />
        <path d="M8 9H16M8 13H12"
            stroke="url(#advisorGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <defs>
            <linearGradient id="advisorGradient" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                <stop stopColor="#818cf8" />
                <stop offset="1" stopColor="#c084fc" />
            </linearGradient>
            <linearGradient id="advisorFill" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                <stop stopColor="#818cf8" stopOpacity="0.2" />
                <stop offset="1" stopColor="#c084fc" stopOpacity="0.2" />
            </linearGradient>
        </defs>
    </svg>
);

export const RobotIcon = ({ width = "1em", height = "1em", style = {} }) => (
    <svg width={width} height={height} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ verticalAlign: 'middle', ...style }}>
        <path d="M12 2A2 2 0 0 1 14 4V6H10V4A2 2 0 0 1 12 2M21 16L22.5 15.5L21.5 12.5L20 13V12C20 8.69 16.42 6 12 6C7.58 6 4 8.69 4 12V13L2.5 12.5L1.5 15.5L3 16V22H21V16ZM15 13C16.1 13 17 13.9 17 15C17 16.1 16.1 17 15 17C13.9 17 13 16.1 13 15C13 13.9 13.9 13 15 13ZM9 13C10.1 13 11 13.9 11 15C11 16.1 10.1 17 9 17C7.9 17 7 16.1 7 15C7 13.9 7.9 13 9 13Z"
            stroke="url(#robotGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="url(#robotFill)" />
        <defs>
            <linearGradient id="robotGradient" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                <stop stopColor="#34d399" />
                <stop offset="1" stopColor="#3b82f6" />
            </linearGradient>
            <linearGradient id="robotFill" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                <stop stopColor="#34d399" stopOpacity="0.2" />
                <stop offset="1" stopColor="#3b82f6" stopOpacity="0.2" />
            </linearGradient>
        </defs>
    </svg>
);

export const ShieldIcon = ({ width = "1em", height = "1em", style = {} }) => (
    <svg width={width} height={height} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ verticalAlign: 'middle', ...style }}>
        <path d="M12 2L4 5V11.09C4 16.14 7.41 20.53 12 22C16.59 20.53 20 16.14 20 11.09V5L12 2Z"
            stroke="url(#shieldGradient)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="url(#shieldFill)" />
        <defs>
            <linearGradient id="shieldGradient" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
                <stop stopColor="#6366f1" />
                <stop offset="1" stopColor="#ec4899" />
            </linearGradient>
            <linearGradient id="shieldFill" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
                <stop stopColor="#6366f1" stopOpacity="0.2" />
                <stop offset="1" stopColor="#ec4899" stopOpacity="0.2" />
            </linearGradient>
        </defs>
    </svg>
);

export const GroupIcon = ({ width = "1em", height = "1em", style = {} }) => (
    <span style={{ fontSize: width, lineHeight: height, ...style }} role="img" aria-label="Group Tracking">🕵️</span>
);
