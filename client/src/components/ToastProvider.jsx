import { createContext, useContext, useEffect, useState, useSyncExternalStore } from 'react';
import PropTypes from 'prop-types';
import { useAuth } from '../auth/AuthContext';
import { createToastStore } from './toastStore';
import './toast.css';

const ToastContext = createContext(null);

function ToastIcon({ type }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      {type === 'success' ? <path d="m8 12 2.5 2.5L16 9" /> : <>
        <path d="M12 11v5" /><path d="M12 7.5v.01" />
      </>}
    </svg>
  );
}

export function ToastProvider({ children }) {
  const [toast] = useState(() => createToastStore());
  const state = useSyncExternalStore(toast.subscribe, toast.getSnapshot);
  const { user } = useAuth();

  useEffect(() => {
    // Pending deletions are canceled when the signed-in account changes.
    toast.clear();
  }, [toast, user?.id]);

  useEffect(() => {
    const visibility = () => document.hidden ? toast.pause('hidden') : toast.resume('hidden');
    const beforeUnload = (event) => {
      if (toast.hasPending()) {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    visibility();
    document.addEventListener('visibilitychange', visibility);
    window.addEventListener('beforeunload', beforeUnload);
    return () => {
      document.removeEventListener('visibilitychange', visibility);
      window.removeEventListener('beforeunload', beforeUnload);
    };
  }, [toast]);

  return (
    <ToastContext.Provider value={{ toast, hiddenKeys: state.hiddenKeys }}>
      {children}
      <section className="toast-region" aria-label="Notifications" tabIndex={-1}
        onMouseEnter={() => toast.pause('hover')}
        onMouseLeave={() => toast.resume('hover')}
        onFocus={() => toast.pause('focus')}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) toast.resume('focus');
        }}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            const latest = state.toasts.at(-1);
            // Escape never confirms a pending deletion.
            if (latest && !latest.commit) toast.dismiss(latest.id);
          }
        }}>
        {state.toasts.map((item) => (
          <div key={item.id} className={`toast toast--${item.type}`} data-testid="toast" aria-busy={item.status === 'working'}>
            <span className={`toast-icon ${item.status === 'working' ? 'toast-icon--loading' : ''}`}>
              {item.status === 'working' ? <span className="toast-spinner" /> : <ToastIcon type={item.type} />}
            </span>
            <div className="toast-copy" role={item.type === 'error' ? 'alert' : 'status'} aria-atomic="true">
              <p className="toast-title">{item.message}</p>
              {item.description && <p className="toast-description">{item.description}</p>}
            </div>
            {(item.action || item.commit) && (
              <button type="button" className="toast-action" disabled={item.status === 'working'} onClick={(event) => {
                event.currentTarget.blur();
                toast.action(item.id);
              }}>
                {item.status === 'working' ? 'Working…' : item.actionLabel || 'Undo'}
              </button>
            )}
            <button type="button" className="toast-close" disabled={item.status === 'working'}
              aria-label={item.commit ? 'Dismiss and finish deletion' : 'Dismiss notification'}
              title={item.commit ? 'Dismiss and finish deletion' : 'Dismiss notification'} onClick={(event) => {
                event.currentTarget.blur();
                toast.dismiss(item.id);
              }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
            </button>
            {item.duration > 0 && item.status === 'visible' && (
              <span className="toast-progress" aria-hidden="true"><span style={{
                animationDuration: `${item.duration}ms`,
                animationPlayState: item.paused ? 'paused' : 'running',
              }} /></span>
            )}
          </div>
        ))}
      </section>
    </ToastContext.Provider>
  );
}

ToastIcon.propTypes = { type: PropTypes.string.isRequired };
ToastProvider.propTypes = { children: PropTypes.node.isRequired };

export function useToast() {
  const value = useContext(ToastContext);
  if (!value) throw new Error('useToast must be used inside ToastProvider');
  return value;
}
