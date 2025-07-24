#!/usr/bin/env python3
"""
Real-time Progress Tracking for PDF Processing
Handles WebSocket connections and progress updates for UI
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ProgressUpdate:
    """Structured progress update for PDF processing"""
    timestamp: str
    message: str
    type: str  # info, processing, success, warning, error, progress
    current_page: int
    total_pages: int
    progress_percentage: int
    details: Dict = None
    
    def to_dict(self):
        return asdict(self)

class PDFProgressTracker:
    """
    Centralized progress tracking for PDF processing operations
    Supports multiple concurrent processing jobs with unique session IDs
    """
    
    def __init__(self):
        self.active_sessions = {}  # session_id -> progress_data
        self.session_callbacks = {}  # session_id -> callback_function
        
    def create_session(self, session_id: str, callback: Optional[Callable] = None) -> str:
        """Create a new progress tracking session"""
        self.active_sessions[session_id] = {
            "created_at": datetime.now(),
            "status": "initialized",
            "updates": [],
            "current_progress": 0
        }
        
        if callback:
            self.session_callbacks[session_id] = callback
            
        logger.info(f"Created progress tracking session: {session_id}")
        return session_id
    
    async def update_progress(self, session_id: str, update: ProgressUpdate):
        """Update progress for a specific session"""
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found")
            return
        
        # Store the update
        self.active_sessions[session_id]["updates"].append(update.to_dict())
        self.active_sessions[session_id]["current_progress"] = update.progress_percentage
        self.active_sessions[session_id]["last_update"] = datetime.now()
        
        # Log the update
        logger.info(f"[{session_id}] {update.message}")
        
        # Call the callback if available - but prevent recursion
        if session_id in self.session_callbacks:
            try:
                callback = self.session_callbacks[session_id]
                # Only call if it's not the same callback to prevent recursion
                if hasattr(callback, '__name__') and 'callback' not in callback.__name__.lower():
                    await callback(update.to_dict())
                elif not hasattr(callback, '__name__'):
                    await callback(update.to_dict())
            except RecursionError:
                logger.error(f"Recursion detected in progress callback for {session_id}, skipping")
            except Exception as e:
                logger.error(f"Error calling progress callback for {session_id}: {e}")
    
    def get_session_progress(self, session_id: str) -> Optional[Dict]:
        """Get current progress for a session"""
        return self.active_sessions.get(session_id)
    
    def complete_session(self, session_id: str, final_message: str = "Processing completed"):
        """Mark a session as completed"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["status"] = "completed"
            self.active_sessions[session_id]["completed_at"] = datetime.now()
            logger.info(f"Completed session {session_id}: {final_message}")
    
    def cleanup_session(self, session_id: str):
        """Clean up a completed session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.session_callbacks:
            del self.session_callbacks[session_id]
        logger.info(f"Cleaned up session {session_id}")

# Global progress tracker instance
progress_tracker = PDFProgressTracker()

def create_progress_callback(session_id: str):
    """Create a progress callback function for a specific session"""
    async def callback(progress_data: Dict):
        update = ProgressUpdate(
            timestamp=progress_data.get("timestamp", datetime.now().strftime("%H:%M:%S")),
            message=progress_data.get("message", ""),
            type=progress_data.get("type", "info"),
            current_page=progress_data.get("current_page", 0),
            total_pages=progress_data.get("total_pages", 0),
            progress_percentage=progress_data.get("progress_percentage", 0),
            details=progress_data.get("details", {})
        )
        await progress_tracker.update_progress(session_id, update)
    
    return callback

async def log_processing_step(session_id: str, message: str, step_type: str = "info", 
                            current_page: int = 0, total_pages: int = 0, details: Dict = None):
    """Helper function to log processing steps"""
    progress_percentage = int((current_page / max(total_pages, 1)) * 100) if total_pages > 0 else 0
    
    update = ProgressUpdate(
        timestamp=datetime.now().strftime("%H:%M:%S"),
        message=message,
        type=step_type,
        current_page=current_page,
        total_pages=total_pages,
        progress_percentage=progress_percentage,
        details=details or {}
    )
    
    await progress_tracker.update_progress(session_id, update)

# WebSocket-compatible progress streaming
class ProgressStreamer:
    """
    Stream progress updates to connected clients (WebSocket, SSE, etc.)
    """
    
    def __init__(self):
        self.connected_clients = {}  # session_id -> [client_connections]
    
    def add_client(self, session_id: str, client_connection):
        """Add a client connection for progress updates"""
        if session_id not in self.connected_clients:
            self.connected_clients[session_id] = []
        self.connected_clients[session_id].append(client_connection)
    
    def remove_client(self, session_id: str, client_connection):
        """Remove a client connection"""
        if session_id in self.connected_clients:
            if client_connection in self.connected_clients[session_id]:
                self.connected_clients[session_id].remove(client_connection)
            
            # Clean up empty session
            if not self.connected_clients[session_id]:
                del self.connected_clients[session_id]
    
    async def broadcast_update(self, session_id: str, update_data: Dict):
        """Broadcast progress update to all connected clients"""
        if session_id not in self.connected_clients:
            return
        
        # Send to all connected clients for this session
        disconnected_clients = []
        for client in self.connected_clients[session_id]:
            try:
                await client.send_text(json.dumps(update_data))
            except Exception as e:
                logger.warning(f"Failed to send update to client: {e}")
                disconnected_clients.append(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.remove_client(session_id, client)

# Global progress streamer
progress_streamer = ProgressStreamer()

# Example usage for integration with VisionPDFProcessor
async def create_pdf_progress_callback(session_id: str):
    """Create a progress callback that integrates with the PDF processor"""
    
    async def pdf_progress_callback(progress_data: Dict):
        """Handle progress updates from PDF processor"""
        
        # Create structured update
        update = ProgressUpdate(
            timestamp=progress_data.get("timestamp", datetime.now().strftime("%H:%M:%S")),
            message=progress_data.get("message", ""),
            type=progress_data.get("type", "info"),
            current_page=progress_data.get("current_page", 0),
            total_pages=progress_data.get("total_pages", 0),
            progress_percentage=progress_data.get("progress_percentage", 0),
            details=progress_data.get("details", {})
        )
        
        # Update tracker
        await progress_tracker.update_progress(session_id, update)
        
        # Broadcast to connected clients
        await progress_streamer.broadcast_update(session_id, update.to_dict())
        
        # Additional logging for specific events
        if update.type == "success" and "questions_found" in update.details:
            logger.info(f"Session {session_id}: Found {update.details['questions_found']} questions on page {update.current_page}")
        
        if update.type == "error":
            logger.error(f"Session {session_id}: Error - {update.message}")
    
    return pdf_progress_callback
