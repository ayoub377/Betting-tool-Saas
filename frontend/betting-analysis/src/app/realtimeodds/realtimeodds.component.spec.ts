import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RealtimeoddsComponent } from './realtimeodds.component';

describe('RealtimeoddsComponent', () => {
  let component: RealtimeoddsComponent;
  let fixture: ComponentFixture<RealtimeoddsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RealtimeoddsComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(RealtimeoddsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
