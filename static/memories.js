// Memories Archive - Interactive Elements

document.addEventListener('DOMContentLoaded', function() {
    // Initialize desk item interactions
    initializeDeskItems();
    
    // Initialize scroll fade animations
    initializeScrollFade();
});

/**
 * Initialize hover interactions for desk items
 */
function initializeDeskItems() {
    const deskItems = document.querySelectorAll('.desk-item');
    const memoryReveal = document.querySelector('.memory-reveal');
    
    deskItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            const memory = this.getAttribute('data-memory');
            if (memory && memoryReveal) {
                memoryReveal.textContent = `"${memory}"`;
                memoryReveal.classList.add('active');
            }
        });
        
        item.addEventListener('mouseleave', function() {
            if (memoryReveal) {
                memoryReveal.classList.remove('active');
                setTimeout(() => {
                    memoryReveal.textContent = '';
                }, 400);
            }
        });
    });
}

/**
 * Initialize scroll fade animations using Intersection Observer
 */
function initializeScrollFade() {
    const scrollFadeElements = document.querySelectorAll('.scroll-fade');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Calculate delay based on position
                const delay = entry.target.getAttribute('data-delay') || '0';
                entry.target.style.animationDelay = `${delay}s`;
                entry.target.classList.add('active');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });
    
    scrollFadeElements.forEach(element => {
        observer.observe(element);
    });
}

/**
 * Smooth scroll observer for subtle effects
 */
window.addEventListener('scroll', function() {
    const sections = document.querySelectorAll('section');
    
    sections.forEach(section => {
        const rect = section.getBoundingClientRect();
        const isVisible = rect.top < window.innerHeight && rect.bottom > 0;
        
        if (isVisible) {
            const scrollPercent = (window.innerHeight - rect.top) / (window.innerHeight + rect.height);
            // Could be used for subtle parallax or opacity changes
        }
    });
});

// Keyboard navigation support
document.addEventListener('keydown', function(event) {
    // Allow users to navigate desk items with arrow keys
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        const deskItems = Array.from(document.querySelectorAll('.desk-item'));
        const activeElement = document.activeElement;
        
        if (deskItems.includes(activeElement)) {
            const currentIndex = deskItems.indexOf(activeElement);
            let nextIndex;
            
            if (event.key === 'ArrowLeft') {
                nextIndex = currentIndex > 0 ? currentIndex - 1 : deskItems.length - 1;
            } else {
                nextIndex = currentIndex < deskItems.length - 1 ? currentIndex + 1 : 0;
            }
            
            deskItems[nextIndex].focus();
        }
    }
});

// Focus styles for accessibility
const deskItems = document.querySelectorAll('.desk-item');
deskItems.forEach(item => {
    item.setAttribute('tabindex', '0');
    
    item.addEventListener('focus', function() {
        const memory = this.getAttribute('data-memory');
        const memoryReveal = document.querySelector('.memory-reveal');
        
        if (memory && memoryReveal) {
            memoryReveal.textContent = `"${memory}"`;
            memoryReveal.classList.add('active');
        }
    });
    
    item.addEventListener('blur', function() {
        const memoryReveal = document.querySelector('.memory-reveal');
        if (memoryReveal) {
            memoryReveal.classList.remove('active');
            setTimeout(() => {
                memoryReveal.textContent = '';
            }, 400);
        }
    });
});

/**
 * Load approved founder memories from API
 */
async function loadFounderMemories() {
    try {
        const response = await fetch('/founder-memory/list');
        if (!response.ok) throw new Error('Failed to load memories');
        
        const memories = await response.json();
        renderMemoryCards(memories);
    } catch (error) {
        console.error('Error loading memories:', error);
    }
}

/**
 * Render memory cards in the Memory Wall
 */
function renderMemoryCards(memories) {
    const container = document.getElementById('memory-wall');
    if (!container) return;
    
    if (memories.length === 0) {
        container.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--text-muted);">Memories will appear here as they are shared and approved.</p>';
        return;
    }
    
    container.innerHTML = memories.map((memory, index) => `
        <div class="memory-card">
            <div class="memory-id">MEMORY #${String(index + 1).padStart(3, '0')}</div>
            <p class="memory-quote">"${memory.text}"</p>
        </div>
    `).join('');
}

/**
 * Initialize memory submission form
 */
function initializeMemoryForm() {
    const form = document.getElementById('memory-form');
    const textarea = document.getElementById('memory-text');
    const message = document.getElementById('submission-message');
    
    if (!form) return; // Form only appears for logged-in users
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const text = textarea.value.trim();
        
        if (!text || text.length < 10 || text.length > 500) {
            message.textContent = 'Memory must be 10-500 characters';
            message.style.color = '#ff6b6b';
            return;
        }
        
        try {
            const response = await fetch('/founder-memory/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text })
            });
            
            if (response.ok) {
                message.textContent = '✓ Memory submitted for review. Thank you!';
                message.style.color = '#8bc34a';
                textarea.value = '';
                setTimeout(() => {
                    message.textContent = '';
                }, 3000);
            } else {
                message.textContent = 'Error submitting memory. Please try again.';
                message.style.color = '#ff6b6b';
            }
        } catch (error) {
            console.error('Error submitting memory:', error);
            message.textContent = 'Error submitting memory';
            message.style.color = '#ff6b6b';
        }
    });
}

/**
 * Initialize archive room scroll effect
 */
function initializeArchiveRoom() {
    const archiveRoom = document.querySelector('.final-archive-room');
    if (!archiveRoom) return;
    
    window.addEventListener('scroll', () => {
        const rect = archiveRoom.getBoundingClientRect();
        if (rect.top < window.innerHeight && rect.bottom > 0) {
            const scrollPercent = (window.innerHeight - rect.top) / (window.innerHeight + rect.height);
            const fade = Math.min(scrollPercent, 1);
            archiveRoom.style.opacity = fade;
        }
    });
}

// Initialize memory features when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    loadFounderMemories();
    initializeMemoryForm();
    initializeArchiveRoom();
});
