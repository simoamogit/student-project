// Inizializza animazioni
document.addEventListener('DOMContentLoaded', () => {
    // Effetto ripple per tutti i pulsanti
    document.querySelectorAll('.btn').forEach(btn => {
      btn.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        ripple.classList.add('ripple-effect');
        
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        ripple.style.width = ripple.style.height = `${size}px`;
        ripple.style.left = `${e.clientX - rect.left - size/2}px`;
        ripple.style.top = `${e.clientY - rect.top - size/2}px`;
        
        this.appendChild(ripple);
        setTimeout(() => ripple.remove(), 600);
      });
    });
  
    // Animazione progressiva elementi
    document.querySelectorAll('.animate-stagger').forEach((el, i) => {
      el.style.animationDelay = `${i * 0.15}s`;
    });
  
    // Effetto parallax
    window.addEventListener('mousemove', (e) => {
      const x = e.clientX / window.innerWidth;
      const y = e.clientY / window.innerHeight;
      document.querySelector('.card-header').style.transform = 
        `translate(${x * 10}px, ${y * 10}px)`;
    });
  
    // Animazione badge al caricamento
    document.querySelectorAll('.badge').forEach((badge, i) => {
      setTimeout(() => {
        badge.classList.add('badge-pop');
      }, 200 * i);
    });
  });