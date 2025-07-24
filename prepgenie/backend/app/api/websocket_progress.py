#!/usr/bin/env python3
"""
WebSocket Progress Tracking for PDF Processing
Provides real-time updates to the frontend during long-running PDF processing tasks
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

logger = logging.getLogger(__name__)

# Global connection manager for WebSocket connections
class ProgressConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.processing_tasks: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[task_id] = websocket
        logger.info(f"📡 WebSocket connected for task: {task_id}")
        
        # Send initial connection confirmation
        await self.send_progress_update(task_id, {
            "type": "connection",
            "message": "Connected to progress tracker",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        })
    
    async def disconnect(self, task_id: str):
        """Remove WebSocket connection"""
        if task_id in self.active_connections:
            del self.active_connections[task_id]
            logger.info(f"📡 WebSocket disconnected for task: {task_id}")
        
        if task_id in self.processing_tasks:
            del self.processing_tasks[task_id]
    
    async def send_progress_update(self, task_id: str, progress_data: Dict):
        """Send progress update to connected client"""
        if task_id in self.active_connections:
            try:
                websocket = self.active_connections[task_id]
                await websocket.send_text(json.dumps(progress_data))
                logger.debug(f"📤 Progress sent to {task_id}: {progress_data.get('message', 'Update')}")
            except Exception as e:
                logger.error(f"Failed to send progress update to {task_id}: {e}")
                await self.disconnect(task_id)
    
    async def broadcast_to_all(self, message: Dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for task_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to broadcast to {task_id}: {e}")
                disconnected.append(task_id)
        
        # Clean up disconnected clients
        for task_id in disconnected:
            await self.disconnect(task_id)
    
    def register_task(self, task_id: str, task_info: Dict):
        """Register a new processing task"""
        self.processing_tasks[task_id] = {
            **task_info,
            "started_at": datetime.now().isoformat(),
            "status": "started"
        }
        logger.info(f"📋 Registered processing task: {task_id}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get current status of a processing task"""
        return self.processing_tasks.get(task_id)

# Global instance
progress_manager = ProgressConnectionManager()

# WebSocket router
router = APIRouter()

@router.websocket("/ws/progress/{task_id}")
async def websocket_progress_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for receiving real-time progress updates"""
    await progress_manager.connect(websocket, task_id)
    
    try:
        # Keep connection alive and handle any client messages
        while True:
            try:
                # Wait for client messages (like ping/pong)
                data = await websocket.receive_text()
                client_message = json.loads(data)
                
                # Handle client requests
                if client_message.get("type") == "ping":
                    await progress_manager.send_progress_update(task_id, {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                elif client_message.get("type") == "status_request":
                    task_status = progress_manager.get_task_status(task_id)
                    await progress_manager.send_progress_update(task_id, {
                        "type": "status_response",
                        "task_status": task_status,
                        "timestamp": datetime.now().isoformat()
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break
    
    finally:
        await progress_manager.disconnect(task_id)

# Helper function to create progress callback for PDF processor
def create_progress_callback(task_id: str):
    """Create a progress callback function for the PDF processor"""
    
    async def progress_callback(progress_data: Dict):
        """Callback function that sends progress updates via WebSocket"""
        
        # Enhance progress data with additional info
        enhanced_data = {
            **progress_data,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "type": "progress_update"
        }
        
        # Send to WebSocket client
        await progress_manager.send_progress_update(task_id, enhanced_data)
        
        # Log server-side for debugging
        phase = progress_data.get("phase", "unknown")
        message = progress_data.get("message", "Processing...")
        progress = progress_data.get("progress", 0)
        logger.info(f"📊 [{task_id}] {phase}: {progress}% - {message}")
    
    return progress_callback

# Utility functions for integration
async def start_pdf_processing_with_progress(file_path: str, task_id: str) -> Dict:
    """Start PDF processing with progress tracking"""
    from app.utils.vision_pdf_processor import VisionPDFProcessor
    
    # Register the task
    progress_manager.register_task(task_id, {
        "type": "pdf_processing",
        "file_path": file_path,
        "status": "initializing"
    })
    
    # Create progress callback
    progress_callback = create_progress_callback(task_id)
    
    # Send initial status
    await progress_callback({
        "phase": "initializing",
        "message": "Starting PDF processing...",
        "progress": 0,
        "details": f"Processing: {file_path}"
    })
    
    try:
        # Create processor and run with progress tracking
        processor = VisionPDFProcessor()
        result = await processor.process_pdf_with_vision(file_path, progress_callback)
        
        # Send completion status
        await progress_callback({
            "phase": "completed",
            "message": f"✅ Processing completed successfully! Found {result.get('total_questions', 0)} questions",
            "progress": 100,
            "details": "Ready for comprehensive evaluation"
        })
        
        return result
        
    except Exception as e:
        # Send error status
        await progress_callback({
            "phase": "error",
            "message": f"❌ Processing failed: {str(e)}",
            "progress": 0,
            "details": f"Error: {str(e)}"
        })
        raise

# Export manager for use in other modules
__all__ = ["router", "progress_manager", "create_progress_callback", "start_pdf_processing_with_progress"]
