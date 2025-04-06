// Navegación responsiva
const hamburger = document.querySelector('.hamburger');
const navLinks = document.querySelector('.nav-links');
const ctaButton = document.querySelector('.cta-button');

hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('active');
    ctaButton.classList.toggle('active');
    hamburger.classList.toggle('active');
});

// Navegación suave
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        
        const targetId = this.getAttribute('href');
        const targetElement = document.querySelector(targetId);
        
        if (targetElement) {
            window.scrollTo({
                top: targetElement.offsetTop - 80,
                behavior: 'smooth'
            });
            
            // Cerrar menú móvil si está abierto
            if (navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
                ctaButton.classList.remove('active');
                hamburger.classList.remove('active');
            }
        }
    });
});

// Tabs de comandos
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');

tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        // Remover clase active de todos los botones
        tabButtons.forEach(btn => btn.classList.remove('active'));
        
        // Añadir clase active al botón clickeado
        button.classList.add('active');
        
        // Mostrar el panel correspondiente
        const tabId = button.getAttribute('data-tab');
        
        tabPanes.forEach(pane => {
            pane.classList.remove('active');
            if (pane.id === tabId) {
                pane.classList.add('active');
            }
        });
    });
});

// FAQ Acordeón
const faqItems = document.querySelectorAll('.faq-item');

faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    
    question.addEventListener('click', () => {
        // Cerrar otros items
        faqItems.forEach(otherItem => {
            if (otherItem !== item && otherItem.classList.contains('active')) {
                otherItem.classList.remove('active');
            }
        });
        
        // Toggle el item actual
        item.classList.toggle('active');
    });
});

// Animación de aparición al scroll
const animateOnScroll = () => {
    const elements = document.querySelectorAll('.feature-card, .command-item, .step, .faq-item');
    
    elements.forEach(element => {
        const elementPosition = element.getBoundingClientRect().top;
        const screenPosition = window.innerHeight / 1.3;
        
        if (elementPosition < screenPosition) {
            element.classList.add('animate');
        }
    });
};

// Añadir clase para animación CSS
document.addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    style.textContent = `
        .feature-card, .command-item, .step, .faq-item {
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.5s ease, transform 0.5s ease;
        }
        
        .feature-card.animate, .command-item.animate, .step.animate, .faq-item.animate {
            opacity: 1;
            transform: translateY(0);
        }
    `;
    document.head.appendChild(style);
    
    // Ejecutar animación inicial
    animateOnScroll();
    
    // Añadir evento de scroll
    window.addEventListener('scroll', animateOnScroll);
});

// Navegación activa según la sección visible
const sections = document.querySelectorAll('section');
const navItems = document.querySelectorAll('.nav-links a');

window.addEventListener('scroll', () => {
    let current = '';
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;
        
        if (pageYOffset >= sectionTop - 100) {
            current = section.getAttribute('id');
        }
    });
    
    navItems.forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('href') === `#${current}`) {
            item.classList.add('active');
        }
    });
});

// Añadir clase active al estilo de navegación
document.addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    style.textContent = `
        .nav-links a.active::after {
            width: 100%;
        }
        
        .nav-links a.active {
            color: var(--primary-color);
        }
    `;
    document.head.appendChild(style);
});
