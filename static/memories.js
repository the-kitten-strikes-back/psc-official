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
