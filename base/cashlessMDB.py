'''
Python Script to interface MDB-USB as master with cashless reader as slave.
Adapté pour fonctionner en tant que module thread-safe avec callback.

Usage:
    manager = MDBManager(callback=ma_fonction_callback)
    manager.start()
    manager.start_payment(1.50)  # Montant en euros
'''

import serial
import io
import time
import argparse
import sys
import os
import threading
import queue
import logging

VEND_TIMEOUT = 10  # SECONDES

# Variables globales
ser = None
sio = None
debug = False
args = None

class MDBManager:
    """Manager thread-safe pour les transactions MDB"""
    
    def __init__(self, port='/dev/ttyACM0', debug_mode=False, callback=None):
        """
        Initialiser le manager MDB
        
        Args:
            port: Port série (défaut: /dev/ttyACM0)
            debug_mode: Mode debug
            callback: Fonction callback appelée avec (event, data)
                     event: 'PAYMENT_APPROVED', 'PAYMENT_FAILED'
                     data: Montant de la transaction
        """
        self.port = port
        self.debug = debug_mode
        self.callback = callback
        self.payment_queue = queue.Queue()
        self.running = False
        self.worker_thread = None
        self.current_transaction = None
        self.initialized = False
        
        # Configuration du logging
        self.logger = logging.getLogger('MDBManager')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    def start(self):
        """Démarrer le manager et initialiser la communication série"""
        if self.running:
            self.logger.warning("Manager déjà en cours d'exécution")
            return False
            
        try:
            # Initialiser la communication série
            global ser, sio, debug, args
            debug = self.debug
            
            # Simuler les arguments pour la compatibilité
            class Args:
                def __init__(self, port, debug):
                    self.port = port
                    self.debug = debug
                    self.console_out = 1
            
            args = Args(self.port, int(self.debug))
            
            ser = serial.Serial()
            ser.baudrate = 115200
            ser.timeout = 1
            ser.port = self.port
            
            self.logger.info(f"Ouverture du port série: {self.port}")
            ser.open()
            time.sleep(1)  # Attendre l'établissement de la communication
            
            sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
            
            # Initialiser les appareils MDB
            self._init_devices()
            
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            
            self.initialized = True
            self.logger.info("MDB Manager démarré avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur démarrage MDB Manager: {str(e)}")
            self.stop()
            return False
    
    def stop(self):
        """Arrêter le manager et fermer la communication"""
        self.running = False
        if self.worker_thread:
            self.payment_queue.put(('STOP', None))
            self.worker_thread.join(timeout=5)
        
        if self.initialized:
            self._end_communication()
        
        if ser and ser.is_open:
            ser.close()
            
        self.logger.info("MDB Manager arrêté")
    
    def start_payment(self, amount):
        """
        Démarrer une transaction de paiement
        
        Args:
            amount: Montant en euros (ex: 1.50)
        """
        if not self.initialized:
            self.logger.error("Manager non initialisé")
            if self.callback:
                self.callback('PAYMENT_FAILED', {'error': 'Manager non initialisé', 'amount': amount})
            return False
            
        if self.current_transaction:
            self.logger.warning("Transaction déjà en cours")
            return False
            
        self.logger.info(f"Démarrage transaction: {amount}€")
        self.current_transaction = {
            'amount': amount,
            'product': '1',
            'start_time': time.time(),
            'status': 'pending'
        }
        
        self.payment_queue.put(('START_PAYMENT', amount))
        return True
    
    def confirm_service(self):
        """Confirmer que le service a été délivré avec succès"""
        if not self.current_transaction:
            self.logger.warning("Aucune transaction en cours à confirmer")
            return False
            
        if self.current_transaction['status'] != 'approved':
            self.logger.warning(f"Transaction non approuvée (status: {self.current_transaction['status']})")
            return False
            
        self.logger.info("Confirmation du service")
        self.payment_queue.put(('CONFIRM_SERVICE', None))
        return True
    
    def cancel_service(self):
        """Annuler le service (en cas d'erreur)"""
        if not self.current_transaction:
            self.logger.warning("Aucune transaction en cours à annuler")
            return False
            
        self.logger.info("Annulation du service")
        self.payment_queue.put(('CANCEL_SERVICE', None))
        return True
    
    def _worker(self):
        """Thread worker pour gérer les transactions"""
        self.logger.info("Thread worker démarré")
        
        while self.running:
            try:
                cmd, data = self.payment_queue.get(timeout=0.5)
                
                if cmd == 'STOP':
                    break
                elif cmd == 'START_PAYMENT':
                    self._process_payment(data)
                elif cmd == 'CONFIRM_SERVICE':
                    self._confirm_transaction()
                elif cmd == 'CANCEL_SERVICE':
                    self._cancel_transaction()
                    
            except queue.Empty:
                # Pas de timeout global, le terminal CB gère son propre timeout
                continue
                
            except Exception as e:
                self.logger.error(f"Erreur dans worker: {str(e)}")
                
        self.logger.info("Thread worker terminé")
    
    def _process_payment(self, amount):
        """Traiter un paiement"""
        self.logger.info(f"Traitement paiement: {amount}€")
        
        try:
            # Réinitialiser les appareils
            self._init_devices()
            
            # Détecter si le terminal supporte le Direct Vend
            direct = self._detect_direct_vend(str(amount), "1")
            
            if not direct:
                # Mode normal (attente carte/pièces)
                self._normal_vend(str(amount), "1")
            else:
                # Mode Direct Vend
                self._direct_vend(str(amount), "1")
                
        except Exception as e:
            self.logger.error(f"Erreur traitement paiement: {str(e)}")
            if self.callback:
                self.callback('PAYMENT_FAILED', {
                    'error': str(e),
                    'amount': amount
                })
            self.current_transaction = None
    
    def _direct_vend(self, amount, product):
        """Traiter un paiement en mode Direct Vend"""
        self.logger.info("Mode Direct Vend détecté")
        
        while self.running and self.current_transaction:
            try:
                res = self._read_wait()
                if not res:
                    time.sleep(0.1)
                    continue
                    
                self.logger.debug(f"Réponse MDB: {res}")
                
                # Vérifier le résultat de la transaction
                if "d,STATUS,RESULT," in res:
                    if "d,STATUS,RESULT,1" in res or "SUCCESS" in res:
                        # Paiement accepté !
                        self.logger.info(f"Paiement accepté: {amount}€")
                        self.current_transaction['status'] = 'approved'
                        
                        if self.callback:
                            self.callback('PAYMENT_APPROVED', {
                                'amount': float(amount),
                                'timestamp': time.time(),
                                'response': res.strip()
                            })
                        
                        # Attendre confirmation du service
                        # Le terminal CB attend maintenant notre réponse
                        break
                        
                    else:
                        # Paiement refusé
                        self.logger.warning(f"Paiement refusé: {res}")
                        self.current_transaction['status'] = 'failed'
                        
                        if self.callback:
                            self.callback('PAYMENT_FAILED', {
                                'amount': float(amount),
                                'reason': 'Transaction refusée par le terminal',
                                'response': res.strip()
                            })
                        
                        # Réinitialiser pour prochaine transaction
                        self._reset_for_next_transaction()
                        break
                        
            except Exception as e:
                self.logger.error(f"Erreur lecture MDB: {str(e)}")
                time.sleep(0.5)
    
    def _normal_vend(self, amount, product):
        """Mode normal (pour terminaux sans Direct Vend)"""
        self.logger.info("Mode normal - Attente insertion carte/pièces...")
        
        req_str = f"D,REQ,{amount},{product}\n"
        
        try:
            # Attendre crédit
            while self.running and self.current_transaction:
                res = self._read_wait()
                if not res:
                    time.sleep(0.1)
                    continue
                    
                self.logger.debug(f"Réponse MDB (normal): {res}")
                
                if 'd,STATUS,CREDIT,' in res:
                    # Détecter le montant inséré
                    try:
                        credit_str = res[res.find('d,STATUS,CREDIT,')+16:len(res)-3]
                        cash = float(credit_str)
                        self.logger.info(f"Crédit détecté: {cash}€")
                        
                        if cash >= float(amount):
                            # Assez d'argent, démarrer la vente
                            res_vend = self._write_read(req_str.strip())
                            
                            if 'd,STATUS,VEND' in res_vend:
                                # Transaction en attente de confirmation
                                self.logger.info("Vente démarrée, attente résultat...")
                                # Continuer à écouter le résultat
                                continue
                            
                    except (ValueError, IndexError) as e:
                        self.logger.error(f"Erreur parsing crédit: {str(e)}")
                        
                elif "d,STATUS,RESULT," in res:
                    # Résultat de la transaction
                    if "d,STATUS,RESULT,1" in res or "SUCCESS" in res:
                        self.logger.info(f"Paiement accepté (normal): {amount}€")
                        self.current_transaction['status'] = 'approved'
                        
                        if self.callback:
                            self.callback('PAYMENT_APPROVED', {
                                'amount': float(amount),
                                'timestamp': time.time(),
                                'mode': 'normal',
                                'response': res.strip()
                            })
                        break
                    else:
                        self.logger.warning(f"Paiement refusé (normal): {res}")
                        self.current_transaction['status'] = 'failed'
                        
                        if self.callback:
                            self.callback('PAYMENT_FAILED', {
                                'amount': float(amount),
                                'reason': 'Transaction refusée',
                                'mode': 'normal',
                                'response': res.strip()
                            })
                        
                        self._reset_for_next_transaction()
                        break
                        
        except Exception as e:
            self.logger.error(f"Erreur mode normal: {str(e)}")
            if self.callback:
                self.callback('PAYMENT_FAILED', {
                    'amount': float(amount),
                    'error': str(e),
                    'mode': 'normal'
                })
            self.current_transaction = None
    
    def _confirm_transaction(self):
        """Confirmer la transaction après service réussi"""
        if not self.current_transaction or self.current_transaction['status'] != 'approved':
            self.logger.warning("Tentative de confirmation sans transaction approuvée")
            return False
            
        try:
            self.logger.info("Finalisation transaction après service réussi")
            
            # Envoyer la commande de fin (confirmation)
            res = self._write_read("D,END")
            self.logger.debug(f"Confirmation transaction: {res}")
            
            if 'SUCCESS' in res or 'd,STATUS,IDLE' in res:
                transaction = self.current_transaction.copy()
                self._reset_for_next_transaction()
                
                self.logger.info(f"Transaction {transaction['amount']}€ confirmée avec succès")
                return True
            else:
                self.logger.error(f"Erreur confirmation: {res}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur confirmation transaction: {str(e)}")
            return False
    
    def _cancel_transaction(self):
        """Annuler la transaction après échec de service"""
        if not self.current_transaction:
            self.logger.warning("Aucune transaction à annuler")
            return False
            
        try:
            self.logger.info("Annulation transaction")
            
            # Envoyer commande d'annulation
            res = self._write_read("D,END,-1")
            self.logger.debug(f"Annulation: {res}")
            
            transaction = self.current_transaction.copy()
            self._reset_for_next_transaction()
            
            self.logger.info(f"Transaction {transaction['amount']}€ annulée")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur annulation transaction: {str(e)}")
            return False
    
    def _reset_for_next_transaction(self):
        """Réinitialiser pour la prochaine transaction"""
        if self.current_transaction:
            self.logger.debug(f"Réinitialisation transaction {self.current_transaction['amount']}€")
        self.current_transaction = None
        
        # Remettre le terminal en état IDLE
        #try:
        #    self._init_devices()
        #except Exception as e:
        #    self.logger.error(f"Erreur réinitialisation terminal: {str(e)}")
    
    # Méthodes de communication série
    
    def _read_wait(self):
        """Lire depuis le port série avec attente"""
        global sio
        
        for i in range(5):  # Attendre 500ms max
            try:
                buf = sio.readline()
                
                if buf and len(buf) > 0:
                    if self.debug:
                        self.logger.debug(f"Read: {buf}")
                    return buf
                else:
                    time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Erreur lecture série: {str(e)}")
                return ""
        
        return ""
    
    def _write_serial(self, message):
        """Écrire sur le port série"""
        global sio
        
        if self.debug:
            self.logger.debug(f"Write: {message}")
        
        try:
            sio.write(message + "\n")
            sio.flush()
        except Exception as e:
            self.logger.error(f"Erreur écriture série: {str(e)}")
    
    def _write_read(self, message):
        """Écrire et lire une réponse"""
        self._write_serial(message)
        return self._read_wait()
    
    def _init_devices(self):
        """Initialiser les appareils MDB"""
        res = self._read_wait()
        self.logger.info("Init res: " + res)
        if 'd,STATUS,IDLE' in res:
            self.logger.info("Appareils MDB déjà initialisés (IDLE)")
            return
        
        self.logger.info("Initialisation appareils MDB...")
        
        # Démarrer le master en mode Direct Vend
        res = self._write_read("D,2")
        
        if 'D,ERR,"cashless master is on"' in res:
            self.logger.info("Redémarrage Cashless...")
            self._write_serial("D,0")
            self._write_serial("D,2")
            res = self._read_wait()
        
        # Attendre INIT du slave
        start_time = time.time()
        while 'd,STATUS,INIT' not in res:
            if time.time() - start_time > 30:  # Timeout 30s pour l'initialisation
                self.logger.error("Timeout initialisation MDB")
                raise Exception("Timeout initialisation MDB")
                
            self.logger.debug("Attente STATUS = INIT...")
            res = self._read_wait()
            time.sleep(1)
        
        # Activer le reader
        self._write_serial("D,READER,1")
        
        # Attendre IDLE
        start_time = time.time()
        while 'd,STATUS,IDLE' not in res:
            if time.time() - start_time > 30:  # Timeout 30s pour IDLE
                self.logger.error("Timeout attente IDLE")
                raise Exception("Timeout attente IDLE")
                
            self.logger.debug("Attente STATUS = IDLE...")
            res = self._read_wait()
            time.sleep(1)
        
        self.logger.info("Appareils MDB initialisés (IDLE)")
    
    def _detect_direct_vend(self, amount, product):
        """Détecter si le terminal supporte Direct Vend"""
        res = self._write_read(f"D,REQ,{amount},{product}")
        
        if 'd,ERR,"-1"' in res:
            self.logger.info("Terminal ne supporte pas Direct Vend")
            return False
        elif 'd,STATUS,VEND' in res:
            self.logger.info("Terminal supporte Direct Vend")
            return True
        else:
            self.logger.warning(f"Réponse inconnue pour détection Direct Vend: {res}")
            return False
    
    def _end_communication(self):
        """Terminer la communication MDB"""
        try:
            if self.current_transaction:
                self._cancel_transaction()
                
            self._write_read("D,READER,0")  # Désactiver le reader
            self._write_read("D,0")         # Désactiver le host
            self.logger.info("Communication MDB terminée")
        except Exception as e:
            self.logger.error(f"Erreur fin communication: {str(e)}")

# Fonctions de compatibilité pour l'ancien code
def initCB(port='/dev/ttyACM0', debug_mode=False):
    """Fonction de compatibilité - Initialiser MDB"""
    manager = MDBManager(port=port, debug_mode=debug_mode)
    return manager

# Mode standalone pour tests
if __name__ == "__main__":
    print("Test standalone MDB Manager")
    print("=" * 50)
    
    def test_callback(event, data):
        print(f"\n[Callback] Événement: {event}")
        print(f"[Callback] Données: {data}")
        print("-" * 30)
    
    # Créer et démarrer le manager
    manager = MDBManager(port='/dev/ttyACM0', debug_mode=True, callback=test_callback)
    
    if manager.start():
        print("✓ Manager démarré avec succès")
        print("Appuyez sur:")
        print("  1. Démarrer transaction 0.16€")
        print("  2. Confirmer service (après succès)")
        print("  3. Annuler service")
        print("  q. Quitter")
        
        try:
            while True:
                choice = input("\nVotre choix (1-3, q): ").strip().lower()
                
                if choice == '1':
                    success = manager.start_payment(0.16)
                    if success:
                        print("✓ Transaction démarrée")
                    else:
                        print("✗ Échec démarrage transaction")
                        
                elif choice == '2':
                    success = manager.confirm_service()
                    if success:
                        print("✓ Service confirmé")
                    else:
                        print("✗ Échec confirmation")
                        
                elif choice == '3':
                    success = manager.cancel_service()
                    if success:
                        print("✓ Service annulé")
                    else:
                        print("✗ Échec annulation")
                        
                elif choice == 'q':
                    print("Arrêt...")
                    break
                    
                else:
                    print("Choix invalide")
                    
        except KeyboardInterrupt:
            print("\nArrêt par Ctrl+C...")
        finally:
            manager.stop()
            print("Manager arrêté")
    else:
        print("✗ Échec démarrage manager")