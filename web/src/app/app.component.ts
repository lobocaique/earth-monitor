import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { translations, Lang } from './translations';

@Component({
  selector: 'app-root',
  template: `
    <div class="container">
      <header class="header">
        <h1 class="title">{{t.title}}</h1>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
            <div class="lang-toggle">
                <button [class.active]="lang === 'en'" (click)="setLang('en')">EN</button>
                <button [class.active]="lang === 'es'" (click)="setLang('es')">ES</button>
                <button [class.active]="lang === 'pt'" (click)="setLang('pt')">PT</button>
            </div>
            <span class="badge">{{t.badge}}</span>
        </div>
      </header>
      
      <!-- Search Card -->
      <div class="card search-card">
        <div class="search-row">
          <input 
            [(ngModel)]="searchText" 
            [placeholder]="t.placeholder"
            class="input-main"
          />
          <button (click)="search()" class="btn-primary radar-btn">{{t.search}}</button>
        </div>
        <p class="helper-text">{{t.helper}}</p>
      </div>

      <!-- Info Section -->
      <div class="info-section">
        <div class="info-title">{{t.infoTitle}}</div>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-icon">📥</span>
            <p>{{t.infoInput}}</p>
          </div>
          <div class="info-item">
            <span class="info-icon">📡</span>
            <p>{{t.infoOutput}}</p>
          </div>
          <div class="info-item">
            <span class="info-icon">🕐</span>
            <p>{{t.infoData}}</p>
          </div>
          <div class="info-item">
            <span class="info-icon">🌍</span>
            <p>{{t.infoSources}}</p>
          </div>
        </div>
      </div>

      <!-- Error/No Results Message -->
      <div class="error-message" *ngIf="searchError">
        <span class="error-icon">ℹ️</span>
        <span>{{searchError}}</span>
      </div>

      <!-- Results -->
      <div class="results-grid animate-reveal" *ngIf="scenes.length > 0">
        <div class="section-label">{{t.results}}</div>
        <p class="section-desc">{{t.resultsDesc}}</p>
        
        <div class="card scene-card" *ngFor="let s of getVisibleScenes()">
          <img [src]="s.imageUrl" [alt]="s.title" class="scene-image" />
          <div class="scene-body">
            <div class="scene-header">
              <span class="scene-id">{{s.id}}</span>
              <span class="scene-date">{{s.date}}</span>
            </div>
            <div class="scene-title">{{s.title}}</div>
            <div class="scene-loc">📍 City: {{s.city}}, {{s.country}}</div>
            <p class="scene-desc">{{s.description}}</p>
            <span class="source-tag">{{s.source}}</span>
          </div>
        </div>
        
        <button 
          *ngIf="maxVisible < scenes.length" 
          (click)="loadMore()" 
          class="btn-secondary load-more-btn"
        >
          Load More Images
        </button>
      </div>
      
      <!-- Hotspots -->
      <div class="stats-section animate-reveal" *ngIf="hotspots.length > 0">
        <div class="section-label">{{t.hotspots}}</div>
        <p class="section-desc">{{t.hotspotsDesc}}</p>
        <div class="stats-grid">
          <div class="card stat-card" *ngFor="let h of hotspots">
            <div class="stat-count">{{h.alertCount}}</div>
            <div class="stat-label">{{h.location}}</div>
            <div class="stat-type">{{h.alertType}}</div>
          </div>
        </div>
        <p class="source-attribution">{{t.hotspotsSource}}</p>
      </div>
    </div>
  `,
  styles: [`
    .container { width: 100%; max-width: 700px; padding: 0 20px; }
    
    /* Header */
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
    .title { font-size: 24px; font-weight: 600; color: var(--color-primary); margin: 0; }
    .badge { font-size: 12px; font-weight: 600; text-transform: uppercase; color: #1b4332; background: #d8f3dc; padding: 6px 10px; border-radius: 20px; }
    
    .lang-toggle { display: flex; gap: 4px; margin-bottom: 4px; }
    .lang-toggle button { background: rgba(0,0,0,0.05); border: none; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; color: #86868b; cursor: pointer; }
    .lang-toggle button.active { background: var(--color-primary); color: white; }

    /* Cards */
    .card { background: var(--color-surface); padding: 24px; border-radius: var(--radius); box-shadow: var(--shadow-md); margin-bottom: 24px; }
    .search-card { padding-bottom: 16px; }
    
    /* Search */
    .search-row { display: flex; gap: 12px; }
    .input-main { flex: 1; padding: 12px 16px; font-size: 16px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg); outline: none; transition: border-color 0.2s; }
    .input-main:focus { border-color: var(--color-primary); }
    .btn-primary { background: var(--color-primary); color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; font-weight: 500; cursor: pointer; }
    .btn-secondary { background: #e0e0e0; color: #333; border: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; width: 100%; margin-bottom: 30px; transition: background 0.2s; }
    .btn-secondary:hover { background: #d0d0d0; }
    .helper-text { font-size: 13px; color: var(--color-text-muted); margin: 12px 0 0 0; }

    /* Info Section */
    .info-section { margin-bottom: 32px; }
    .info-title { font-size: 14px; font-weight: 600; color: var(--color-text-muted); margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .info-item { display: flex; gap: 10px; align-items: flex-start; padding: 12px; background: rgba(0,0,0,0.02); border-radius: 8px; }
    .info-icon { font-size: 18px; }
    .info-item p { margin: 0; font-size: 13px; color: var(--color-text-muted); line-height: 1.5; }

    /* Section Labels */
    .section-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); margin-bottom: 4px; font-weight: 600; }
    .section-desc { font-size: 14px; color: var(--color-text-muted); margin: 0 0 16px 0; }

    /* Scene Cards */
    .scene-card { padding: 0; overflow: hidden; display: flex; flex-direction: column; }
    .scene-image { width: 100%; height: 200px; object-fit: cover; background-color: #e8e8ed; }
    .scene-body { padding: 20px; display: flex; flex-direction: column; gap: 6px; }
    .scene-header { display: flex; justify-content: space-between; align-items: center; }
    .scene-id { font-family: monospace; font-size: 12px; color: var(--color-text-muted); }
    .scene-date { font-size: 12px; color: var(--color-text-muted); }
    .scene-title { font-size: 18px; font-weight: 600; color: var(--color-text-main); }
    .scene-loc { font-size: 14px; color: var(--color-accent); font-weight: 500; }
    .scene-desc { margin: 0; font-size: 14px; color: var(--color-text-muted); line-height: 1.5; }
    .source-tag { font-size: 11px; font-weight: 600; padding: 4px 8px; border-radius: 4px; background: #e3f2fd; color: #1565c0; align-self: flex-start; margin-top: 8px; }

    /* Error Message */
    .error-message { display: flex; align-items: center; gap: 10px; padding: 16px 20px; background: #fff3e0; border-radius: 8px; margin-bottom: 24px; }
    .error-icon { font-size: 20px; }
    .error-message span:last-child { font-size: 14px; color: #e65100; }

    /* Stats */
    .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .stat-card { text-align: center; padding: 20px; }
    .stat-count { font-size: 32px; font-weight: 700; color: var(--color-danger-text); margin-bottom: 4px; }
    .stat-label { font-size: 14px; color: var(--color-text-main); font-weight: 600; }
    .stat-type { font-size: 12px; color: var(--color-text-muted); margin-top: 4px; }
    
    /* Source Attribution */
    .source-attribution { font-size: 12px; color: var(--color-text-muted); margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--color-border); }
  `]
})
export class AppComponent {
  searchText = '';
  scenes: any[] = [];
  maxVisible = 2;
  hotspots: any[] = [];
  searchError = '';
  lang: Lang = 'en';

  get t() {
    return translations[this.lang];
  }

  setLang(l: Lang) {
    this.lang = l;
  }

  constructor(private http: HttpClient) {
    // No longer fetching hotspots on load
  }

  getVisibleScenes() {
    return this.scenes.slice(0, this.maxVisible);
  }

  loadMore() {
    this.maxVisible += 1;
  }

  search() {
    this.searchError = '';
    this.scenes = [];
    this.hotspots = [];
    this.maxVisible = 2;

    const query = {
      query: `
        query {
          search(text: "${this.searchText}") {
            id
            title
            location
            city
            country
            imageUrl
            description
            date
            source
          }
        }
      `
    };

    this.http.post('http://localhost:4000/graphql', query).subscribe((res: any) => {
      if (res.data && res.data.search) {
        this.scenes = res.data.search;
        if (this.scenes.length === 0) {
          this.searchError = `No satellite imagery found for "${this.searchText}". Try: snow, flood, urban, forest.`;
        } else {
          // Extract up to 2 unique cities and countries
          let uniqueCities = new Set<string>();
          let uniqueCountries = new Set<string>();
          
          for (let s of this.scenes) {
            if (s.city && s.city !== 'Unknown') uniqueCities.add(s.city);
            if (s.country && s.country !== 'Unknown') uniqueCountries.add(s.country);
          }
          
          let locationsToQuery: string[] = [];
          Array.from(uniqueCities).slice(0, 2).forEach(c => locationsToQuery.push(c));
          Array.from(uniqueCountries).slice(0, 2).forEach(c => locationsToQuery.push(c));
          
          if (locationsToQuery.length > 0) {
            this.fetchHotspots(locationsToQuery);
          }
        }
      }
    }, (err) => {
      this.searchError = 'Unable to connect to satellite data service.';
    });
  }

  fetchHotspots(locations: string[]) {
    const query = {
      query: `
        query($locations: [String]) {
          getHotspots(locations: $locations) {
            location
            alertCount
            alertType
          }
        }
      `,
      variables: { locations }
    };
    
    this.http.post('http://localhost:4000/graphql', query).subscribe((res: any) => {
      if (res.data && res.data.getHotspots) {
        this.hotspots = res.data.getHotspots;
      }
    });
  }
}
