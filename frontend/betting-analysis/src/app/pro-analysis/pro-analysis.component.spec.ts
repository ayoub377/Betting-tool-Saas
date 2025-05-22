import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ProAnalysisComponent } from './pro-analysis.component';

describe('ProAnalysisComponent', () => {
  let component: ProAnalysisComponent;
  let fixture: ComponentFixture<ProAnalysisComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProAnalysisComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(ProAnalysisComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
