/**
 * Setu Web - Firebase Cloud Firestore Client Integration
 * Firebase Project: setu-a767c
 * Enables real-time telemetry streaming, offline cache, orders and audit logs.
 */

(function() {
  'use strict';

  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  const firebaseConfig = {
    apiKey: "AIzaSyB4gmvhHcOaPJ3WjpVXi6S26OS0vFm-zDQ",
    authDomain: isLocal ? "setu-a767c.firebaseapp.com" : window.location.host,
    projectId: "setu-a767c",
    storageBucket: "setu-a767c.firebasestorage.app",
    messagingSenderId: "97434241991",
    appId: "1:97434241991:web:f3efcfd3f68ece773ce7e2",
    measurementId: "G-60C89W64K3"
  };

  let app = null;
  let db = null;
  let auth = null;
  let isInitialized = false;

  function initFirebase() {
    if (typeof firebase === 'undefined') {
      console.warn('[SetuFirebase] Firebase SDK not loaded on window.');
      return false;
    }
    if (!firebase.apps.length) {
      app = firebase.initializeApp(firebaseConfig);
    } else {
      app = firebase.app();
    }
    db = firebase.firestore();
    auth = firebase.auth();
    isInitialized = true;
    console.info('[SetuFirebase] Cloud Firestore initialized for project:', firebaseConfig.projectId);
    if (typeof window.setupFirebaseAuthListeners === 'function') {
      window.setupFirebaseAuthListeners();
    }
    return true;
  }

  // Auto-init if SDK is already loaded
  if (typeof firebase !== 'undefined') {
    initFirebase();
  }

  const SetuFirebase = {
    get isAvailable() {
      if (!isInitialized && typeof firebase !== 'undefined') {
        initFirebase();
      }
      return isInitialized && db !== null;
    },

    get db() {
      if (!db && typeof firebase !== 'undefined') initFirebase();
      return db;
    },

    get auth() {
      if (!auth && typeof firebase !== 'undefined') initFirebase();
      return auth;
    },

    /**
     * Listen in real-time to the latest sensor telemetry for a shed.
     * @param {string} shedId
     * @param {function(object)} onUpdate
     * @param {function(Error)} onError
     * @returns {function()} unsubscribe
     */
    subscribeShedTelemetry(shedId, onUpdate, onError) {
      if (!this.isAvailable) {
        console.warn('[SetuFirebase] Firestore unavailable for subscribeShedTelemetry');
        return () => {};
      }
      return db.collection('shed_telemetry')
        .where('shed_id', '==', shedId)
        .orderBy('timestamp', 'desc')
        .limit(1)
        .onSnapshot((snapshot) => {
          if (!snapshot.empty) {
            const doc = snapshot.docs[0];
            const data = doc.data();
            data.id = doc.id;
            onUpdate(data);
          }
        }, (err) => {
          console.error('[SetuFirebase] Telemetry stream error:', err);
          if (onError) onError(err);
        });
    },

    /**
     * Fetch products catalogue with local cache.
     */
    async getProducts(category) {
      if (!this.isAvailable) return [];
      try {
        let q = db.collection('products');
        if (category && category !== 'All') {
          q = q.where('category', '==', category);
        }
        const snap = await q.get();
        return snap.docs.map(d => ({ id: d.id, ...d.data() }));
      } catch (e) {
        console.error('[SetuFirebase] getProducts error:', e);
        return [];
      }
    },

    /**
     * Fetch user orders.
     */
    async getOrders(userId) {
      if (!this.isAvailable) return [];
      try {
        let q = db.collection('orders');
        if (userId) {
          q = q.where('user_id', '==', userId);
        }
        q = q.orderBy('created_at', 'desc');
        const snap = await q.get();
        return snap.docs.map(d => ({ id: d.id, ...d.data() }));
      } catch (e) {
        console.error('[SetuFirebase] getOrders error:', e);
        return [];
      }
    },

    /**
     * Dispatch actuator command to IoT Gateway via Firestore.
     */
    async issueActuatorCommand(shedId, actuator, state, source = 'web_admin') {
      if (!this.isAvailable) return false;
      try {
        const cmdRef = db.collection('device_commands').doc();
        const nowIso = new Date().toISOString();
        await cmdRef.set({
          command_id: cmdRef.id,
          shed_id: shedId,
          actuator: actuator,
          state: state ? 1 : 0,
          source: source,
          status: 'PENDING',
          created_at: nowIso
        });
        return true;
      } catch (e) {
        console.error('[SetuFirebase] issueActuatorCommand error:', e);
        return false;
      }
    },

    /**
     * Append immutable audit log.
     */
    async logAuditEvent(actor, action, details = {}, ip = '') {
      if (!this.isAvailable) return;
      try {
        const auditRef = db.collection('audit_logs').doc();
        await auditRef.set({
          id: auditRef.id,
          timestamp: firebase.firestore.FieldValue.serverTimestamp(),
          actor: actor,
          action: action,
          details: details,
          ip_address: ip || 'client_web'
        });
      } catch (e) {
        console.warn('[SetuFirebase] Audit log write warning:', e);
      }
    }
  };

  window.SetuFirebase = SetuFirebase;
})();
