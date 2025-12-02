import React, { useState, useEffect } from 'react';
import { Clock, Loader2 } from 'lucide-react';
import './CountdownTimer.css';

const CountdownTimer = ({ duration = 45, onComplete }) => {
    const [timeRemaining, setTimeRemaining] = useState(duration);
    const [isVisible, setIsVisible] = useState(true);

    useEffect(() => {
        if (timeRemaining <= 0) {
            setIsVisible(false);
            if (onComplete) onComplete();
            return;
        }

        const timer = setInterval(() => {
            setTimeRemaining(prev => prev - 1);
        }, 1000);

        return () => clearInterval(timer);
    }, [timeRemaining, onComplete]);

    const getTimeMessage = () => {
        if (timeRemaining > 60) {
            const mins = Math.ceil(timeRemaining / 60);
            return `Less than ${mins} min remaining`;
        } else if (timeRemaining > 30) {
            return 'Less than 1 min remaining';
        } else if (timeRemaining > 10) {
            return 'About 30 seconds';
        } else if (timeRemaining > 5) {
            return 'Almost done...';
        } else {
            return 'Just a moment...';
        }
    };

    if (!isVisible) return null;

    return (
        <div className="countdown-timer">
            <div className="countdown-content">
                <Loader2 className="countdown-icon" size={14} />
                <span className="countdown-text">{getTimeMessage()}</span>
            </div>
        </div>
    );
};

export default CountdownTimer;
