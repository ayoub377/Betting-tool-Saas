// src/components/ui/Button.tsx
import React, { ReactNode } from 'react';
import Link from 'next/link';
import Spinner from './Spinner'; // Import the Spinner

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'link';
  size?: 'sm' | 'md' | 'lg' | 'icon'; // Added 'icon' size
  isLoading?: boolean;
  href?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  className?: string;
}

const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  href,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  type = 'button',
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 transition-colors duration-150 disabled:opacity-60 disabled:cursor-not-allowed';

const variantStyles = {
  primary:
    'bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-blue-500 shadow-sm dark:bg-sky-500 dark:hover:bg-sky-600 dark:focus-visible:ring-sky-400', // Example dark primary
  secondary:
    'bg-gray-200 text-gray-800 hover:bg-gray-300 focus-visible:ring-gray-400 shadow-sm dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600 dark:focus-visible:ring-slate-500',
  outline:
    'border border-blue-600 text-blue-600 hover:bg-blue-50 focus-visible:ring-blue-500 bg-transparent dark:border-sky-500 dark:text-sky-500 dark:hover:bg-sky-900 dark:hover:bg-opacity-50 dark:focus-visible:ring-sky-400',
  ghost:
    'text-gray-700 hover:bg-gray-100 hover:text-gray-900 focus-visible:ring-gray-400 bg-transparent dark:text-gray-400 dark:hover:bg-slate-700 dark:hover:text-slate-200 dark:focus-visible:ring-slate-500',
  danger:
    'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500 shadow-sm dark:bg-red-500 dark:hover:bg-red-600 dark:focus-visible:ring-red-400',
  link: 'text-blue-600 hover:underline focus-visible:ring-blue-500 bg-transparent p-0 dark:text-sky-400 dark:hover:text-sky-300 dark:focus-visible:ring-sky-500',
};

  const sizeStyles = {
    sm: 'px-3 py-1.5 text-sm rounded-md',
    md: 'px-4 py-2 text-base rounded-md',
    lg: 'px-6 py-3 text-lg rounded-lg',
    icon: 'p-2 rounded-md', // For icon-only buttons
  };

  // Link variant should not have padding from sizeStyles unless it's an icon
  const currentSizeStyles = variant === 'link' && size !== 'icon' ? '' : sizeStyles[size];

  const combinedClassName = `
    ${baseStyles}
    ${variantStyles[variant]}
    ${currentSizeStyles}
    ${className}
  `;

  const content = (
    <>
      {isLoading && <Spinner size={size === 'sm' ? 'sm' : 'md'} className={leftIcon || rightIcon || children ? "mr-2" : ""} />}
      {!isLoading && leftIcon && <span className={children ? "mr-2" : ""}>{leftIcon}</span>}
      {!isLoading && children}
      {!isLoading && rightIcon && <span className={children ? "ml-2" : ""}>{rightIcon}</span>}
    </>
  );

  if (href) {
    return (
      <Link href={href} className={combinedClassName} {...(props as any)}>
        {content}
      </Link>
    );
  }

  return (
    <button
      type={type}
      className={combinedClassName}
      disabled={disabled || isLoading}
      {...props}
    >
      {content}
    </button>
  );
};

export default Button;