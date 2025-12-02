import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CheckCircle2, Circle } from 'lucide-react';

const StepCard = ({ step, index, totalSteps, isCompleted, onToggleComplete }) => {
    const stepImages = {
        1: '/images/modem-steps/modem_step1_unpack_1764638660382.png',
        2: '/images/modem-steps/modem_step2_cable_1764638673212.png',
        3: '/images/modem-steps/modem_step3_power_1764638685128.png',
        4: '/images/modem-steps/modem_step4_lights_1764638699123.png',
        5: '/images/modem-steps/modem_step5_ethernet_1764638712846.png',
    };

    return (
        <div className={`step-card ${isCompleted ? 'completed' : ''}`}>
            <div className="step-header">
                <div className="step-number">{step.number}</div>
                <div className="step-title-container">
                    <h4 className="step-title">{step.title}</h4>
                    <span className="step-progress">Step {step.number} of {totalSteps}</span>
                </div>
                <button
                    onClick={() => onToggleComplete(index)}
                    className="complete-button"
                    aria-label={isCompleted ? "Mark as incomplete" : "Mark as complete"}
                >
                    {isCompleted ? (
                        <CheckCircle2 className="text-green-600" size={24} />
                    ) : (
                        <Circle className="text-slate-300" size={24} />
                    )}
                </button>
            </div>

            <div className="step-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {step.description}
                </ReactMarkdown>

                {stepImages[step.number] && (
                    <img
                        src={stepImages[step.number]}
                        alt={`Step ${step.number}: ${step.title}`}
                        className="step-image"
                    />
                )}
            </div>
        </div>
    );
};

export default StepCard;
