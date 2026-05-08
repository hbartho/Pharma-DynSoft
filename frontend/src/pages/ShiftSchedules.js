import React, { useState, useMemo, useEffect } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  Calendar as CalendarIcon, 
  ChevronLeft, 
  ChevronRight, 
  Plus, 
  Trash2, 
  Edit, 
  User, 
  Clock, 
  List, 
  Grid3X3,
  Users,
  Loader2,
  AlertCircle,
  Copy,
  CalendarDays
} from 'lucide-react';
import { 
  useCalendarView, 
  useWeekView, 
  useCreateShiftSchedule, 
  useCreateBulkSchedules,
  useUpdateShiftSchedule,
  useDeleteShiftSchedule 
} from '../hooks/useShiftSchedules';
import { useUsers } from '../hooks/useUsers';
import { toast } from 'sonner';

const ShiftSchedules = () => {
  // États pour la navigation
  const [viewMode, setViewMode] = useState('month'); // 'month' ou 'week'
  const [currentDate, setCurrentDate] = useState(new Date());
  
  // États pour les modales
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  
  // Données
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth() + 1;
  
  // Calculer le premier jour de la semaine
  const getWeekStart = (date) => {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Lundi comme premier jour
    d.setDate(diff);
    return d.toISOString().split('T')[0];
  };
  
  const weekStart = getWeekStart(currentDate);
  
  // Hooks de données
  const { data: calendarData, isLoading: calendarLoading } = useCalendarView(year, month);
  const { data: weekData, isLoading: weekLoading } = useWeekView(weekStart);
  const { data: usersData } = useUsers();
  
  // Mutations
  const createSchedule = useCreateShiftSchedule();
  const createBulkSchedules = useCreateBulkSchedules();
  const updateSchedule = useUpdateShiftSchedule();
  const deleteSchedule = useDeleteShiftSchedule();
  
  // Filtrer les utilisateurs planifiables (non-admin)
  const schedulableUsers = useMemo(() => {
    return (usersData || []).filter(u => u.role !== 'admin' && u.is_active !== false);
  }, [usersData]);
  
  // Navigation
  const navigatePrevious = () => {
    if (viewMode === 'month') {
      setCurrentDate(new Date(year, month - 2, 1));
    } else {
      const newDate = new Date(currentDate);
      newDate.setDate(newDate.getDate() - 7);
      setCurrentDate(newDate);
    }
  };
  
  const navigateNext = () => {
    if (viewMode === 'month') {
      setCurrentDate(new Date(year, month, 1));
    } else {
      const newDate = new Date(currentDate);
      newDate.setDate(newDate.getDate() + 7);
      setCurrentDate(newDate);
    }
  };
  
  const navigateToday = () => {
    setCurrentDate(new Date());
  };
  
  // Générer les jours du mois pour l'affichage calendrier
  const generateMonthDays = () => {
    const firstDay = new Date(year, month - 1, 1);
    const lastDay = new Date(year, month, 0);
    const startDayOfWeek = firstDay.getDay() || 7; // 1 = Lundi, 7 = Dimanche
    
    const days = [];
    
    // Jours du mois précédent
    const prevMonthLastDay = new Date(year, month - 1, 0).getDate();
    for (let i = startDayOfWeek - 1; i > 0; i--) {
      days.push({
        date: `${year}-${String(month - 1 || 12).padStart(2, '0')}-${String(prevMonthLastDay - i + 1).padStart(2, '0')}`,
        isCurrentMonth: false,
        day: prevMonthLastDay - i + 1
      });
    }
    
    // Jours du mois actuel
    for (let i = 1; i <= lastDay.getDate(); i++) {
      const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
      days.push({
        date: dateStr,
        isCurrentMonth: true,
        day: i,
        isToday: dateStr === new Date().toISOString().split('T')[0]
      });
    }
    
    // Jours du mois suivant
    const remainingDays = 42 - days.length; // 6 semaines * 7 jours
    for (let i = 1; i <= remainingDays; i++) {
      days.push({
        date: `${month === 12 ? year + 1 : year}-${String(month === 12 ? 1 : month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`,
        isCurrentMonth: false,
        day: i
      });
    }
    
    return days;
  };
  
  // Générer les jours de la semaine
  const generateWeekDays = () => {
    const days = [];
    const start = new Date(weekStart);
    
    for (let i = 0; i < 7; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      const dateStr = d.toISOString().split('T')[0];
      days.push({
        date: dateStr,
        dayName: d.toLocaleDateString('fr-FR', { weekday: 'short' }),
        dayNumber: d.getDate(),
        isToday: dateStr === new Date().toISOString().split('T')[0],
        isWeekend: d.getDay() === 0 || d.getDay() === 6
      });
    }
    
    return days;
  };
  
  // Obtenir les couleurs par rôle
  const getRoleColor = (role) => {
    switch (role) {
      case 'pharmacien': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'caissier': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };
  
  // Format du mois
  const monthNames = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 
                      'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];
  
  const monthDays = generateMonthDays();
  const weekDays = generateWeekDays();
  
  // État du formulaire
  const [formData, setFormData] = useState({
    user_id: '',
    scheduled_date: '',
    start_time: '08:00',
    end_time: '16:00',
    max_duration_hours: 8,
    notes: ''
  });
  
  // Réinitialiser le formulaire
  const resetForm = () => {
    setFormData({
      user_id: '',
      scheduled_date: selectedDate || '',
      start_time: '08:00',
      end_time: '16:00',
      max_duration_hours: 8,
      notes: ''
    });
  };
  
  // Ouvrir le modal de création
  const handleOpenCreate = (date = null) => {
    setSelectedDate(date);
    setFormData({
      user_id: '',
      scheduled_date: date || new Date().toISOString().split('T')[0],
      start_time: '08:00',
      end_time: '16:00',
      max_duration_hours: 8,
      notes: ''
    });
    setShowCreateModal(true);
  };
  
  // Ouvrir le modal d'édition
  const handleOpenEdit = (schedule) => {
    setSelectedSchedule(schedule);
    setFormData({
      user_id: schedule.user_id,
      scheduled_date: schedule.scheduled_date,
      start_time: schedule.start_time,
      end_time: schedule.end_time,
      max_duration_hours: schedule.max_duration_hours || 8,
      notes: schedule.notes || ''
    });
    setShowEditModal(true);
  };
  
  // Créer une planification
  const handleCreate = async () => {
    if (!formData.user_id || !formData.scheduled_date) {
      toast.error('Veuillez remplir tous les champs obligatoires');
      return;
    }
    
    createSchedule.mutate(formData, {
      onSuccess: () => {
        setShowCreateModal(false);
        resetForm();
      }
    });
  };
  
  // Mettre à jour une planification
  const handleUpdate = async () => {
    if (!selectedSchedule) return;
    
    updateSchedule.mutate({
      scheduleId: selectedSchedule.id,
      data: {
        start_time: formData.start_time,
        end_time: formData.end_time,
        max_duration_hours: formData.max_duration_hours,
        notes: formData.notes
      }
    }, {
      onSuccess: () => {
        setShowEditModal(false);
        setSelectedSchedule(null);
      }
    });
  };
  
  // Supprimer une planification
  const [confirmDelete, setConfirmDelete] = useState(false);
  
  const handleDelete = async (scheduleId) => {
    if (!scheduleId) {
      toast.error('ID de planification manquant');
      return;
    }
    
    // Si pas encore confirmé, demander confirmation
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    
    // Confirmation reçue, procéder à la suppression
    deleteSchedule.mutate(scheduleId, {
      onSuccess: () => {
        setShowEditModal(false);
        setSelectedSchedule(null);
        setConfirmDelete(false);
      },
      onError: () => {
        setConfirmDelete(false);
      }
    });
  };
  
  // Reset confirmDelete quand on ferme la modal
  useEffect(() => {
    if (!showEditModal) {
      setConfirmDelete(false);
    }
  }, [showEditModal]);
  
  // État pour la création en masse
  const [bulkData, setBulkData] = useState({
    user_id: '',
    selectedDays: [], // ['2026-02-03', '2026-02-04', ...]
    start_time: '08:00',
    end_time: '16:00',
    max_duration_hours: 8
  });
  
  // Création en masse
  const handleBulkCreate = async () => {
    if (!bulkData.user_id || bulkData.selectedDays.length === 0) {
      toast.error('Veuillez sélectionner un utilisateur et au moins une date');
      return;
    }
    
    const schedules = bulkData.selectedDays.map(date => ({
      scheduled_date: date,
      start_time: bulkData.start_time,
      end_time: bulkData.end_time,
      max_duration_hours: bulkData.max_duration_hours
    }));
    
    createBulkSchedules.mutate({
      user_id: bulkData.user_id,
      schedules
    }, {
      onSuccess: () => {
        setShowBulkModal(false);
        setBulkData({
          user_id: '',
          selectedDays: [],
          start_time: '08:00',
          end_time: '16:00',
          max_duration_hours: 8
        });
      }
    });
  };
  
  // Toggle jour dans la sélection en masse
  const toggleBulkDay = (date) => {
    setBulkData(prev => ({
      ...prev,
      selectedDays: prev.selectedDays.includes(date)
        ? prev.selectedDays.filter(d => d !== date)
        : [...prev.selectedDays, date]
    }));
  };
  
  const isLoading = viewMode === 'month' ? calendarLoading : weekLoading;
  
  return (
    <Layout>
      <div className="space-y-6" data-testid="shift-schedules-page">
        {/* Header responsive */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-4xl font-bold text-slate-900 mb-1 sm:mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Planification des Shifts
            </h1>
            <p className="text-sm sm:text-base text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gérez les horaires de travail des employés
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowBulkModal(true)}
              className="rounded-full"
              data-testid="bulk-create-btn"
            >
              <Copy className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline">Planification rapide</span>
              <span className="sm:hidden">Rapide</span>
            </Button>
            <Button
              size="sm"
              onClick={() => handleOpenCreate()}
              className="bg-teal-700 hover:bg-teal-800 rounded-full"
              data-testid="new-schedule-btn"
            >
              <Plus className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline">Nouvelle planification</span>
              <span className="sm:hidden">Nouveau</span>
            </Button>
          </div>
        </div>
        
        {/* Navigation et Vue - responsive */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={navigatePrevious}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={navigateToday}>
              Aujourd'hui
            </Button>
            <Button variant="outline" size="sm" onClick={navigateNext}>
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
          
          <h2 className="text-lg sm:text-xl font-semibold text-slate-800 text-center">
            {viewMode === 'month' 
              ? `${monthNames[month - 1]} ${year}`
              : `Semaine du ${new Date(weekStart).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })}`
            }
          </h2>
          
          <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-lg">
            <Button
              variant={viewMode === 'month' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('month')}
              className={viewMode === 'month' ? 'bg-white shadow-sm' : ''}
            >
              <Grid3X3 className="w-4 h-4 sm:mr-1" />
              <span className="hidden sm:inline">Mois</span>
            </Button>
            <Button
              variant={viewMode === 'week' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('week')}
              className={viewMode === 'week' ? 'bg-white shadow-sm' : ''}
            >
              <CalendarDays className="w-4 h-4 sm:mr-1" />
              <span className="hidden sm:inline">Semaine</span>
            </Button>
          </div>
        </div>
        
        {/* Calendrier */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
          </div>
        ) : viewMode === 'month' ? (
          /* Vue Mois */
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            {/* Header des jours */}
            <div className="grid grid-cols-7 bg-slate-50 border-b border-slate-200">
              {['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'].map(day => (
                <div key={day} className="px-2 py-3 text-center text-sm font-medium text-slate-600">
                  {day}
                </div>
              ))}
            </div>
            
            {/* Grille des jours */}
            <div className="grid grid-cols-7">
              {monthDays.map((dayInfo, idx) => {
                const schedules = calendarData?.schedules?.[dayInfo.date] || [];
                
                return (
                  <div
                    key={idx}
                    className={`min-h-[120px] border-b border-r border-slate-100 p-2 ${
                      !dayInfo.isCurrentMonth ? 'bg-slate-50 opacity-50' : ''
                    } ${dayInfo.isToday ? 'bg-teal-50' : ''}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-sm font-medium ${
                        dayInfo.isToday ? 'text-teal-700 bg-teal-200 px-2 py-0.5 rounded-full' : 'text-slate-600'
                      }`}>
                        {dayInfo.day}
                      </span>
                      {dayInfo.isCurrentMonth && (
                        <button
                          onClick={() => handleOpenCreate(dayInfo.date)}
                          className="opacity-0 hover:opacity-100 text-slate-400 hover:text-teal-600 transition-opacity"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                    
                    <div className="space-y-1">
                      {schedules.slice(0, 3).map((schedule, sIdx) => (
                        <div
                          key={sIdx}
                          onClick={() => handleOpenEdit(schedule)}
                          className={`text-xs px-2 py-1.5 rounded cursor-pointer border ${getRoleColor(schedule.role || schedule.user_role)} hover:shadow-sm transition-shadow`}
                          title={`${schedule.user_name} (${schedule.user_code || schedule.employee_code}) - ${schedule.start_time} à ${schedule.end_time}`}
                        >
                          <div className="flex items-center gap-1">
                            <span className="truncate font-medium">{schedule.user_name?.split(' ')[0]}</span>
                            <span className="text-slate-500">-</span>
                            <span className="font-bold">{schedule.user_code || schedule.employee_code}</span>
                          </div>
                          <div className="text-slate-600 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {schedule.start_time} - {schedule.end_time}
                          </div>
                        </div>
                      ))}
                      {schedules.length > 3 && (
                        <div className="text-xs text-slate-500 pl-2">
                          +{schedules.length - 3} autres
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          /* Vue Semaine */
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            {/* Header des jours */}
            <div className="grid grid-cols-8 bg-slate-50 border-b border-slate-200">
              <div className="px-4 py-3 text-sm font-medium text-slate-600 border-r border-slate-200">
                <Users className="w-4 h-4 inline mr-2" />
                Employé
              </div>
              {weekDays.map(day => (
                <div 
                  key={day.date} 
                  className={`px-2 py-3 text-center border-r border-slate-200 last:border-r-0 ${
                    day.isToday ? 'bg-teal-50' : ''
                  } ${day.isWeekend ? 'bg-slate-100' : ''}`}
                >
                  <div className="text-xs text-slate-500">{day.dayName}</div>
                  <div className={`text-lg font-semibold ${day.isToday ? 'text-teal-700' : 'text-slate-800'}`}>
                    {day.dayNumber}
                  </div>
                </div>
              ))}
            </div>
            
            {/* Lignes par utilisateur */}
            {schedulableUsers.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                <AlertCircle className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                <p>Aucun utilisateur planifiable trouvé</p>
              </div>
            ) : (
              schedulableUsers.map(user => {
                const userSchedules = weekData?.schedules_by_user?.find(s => s.user_id === user.id);
                
                return (
                  <div key={user.id} className="grid grid-cols-8 border-b border-slate-100 last:border-b-0">
                    <div className="px-4 py-3 border-r border-slate-200 flex items-center gap-2">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${getRoleColor(user.role)}`}>
                        {user.employee_code?.slice(-3) || '?'}
                      </div>
                      <div>
                        <div className="font-medium text-slate-800 text-sm">{user.name}</div>
                        <div className="text-xs text-slate-500">{user.employee_code}</div>
                      </div>
                    </div>
                    
                    {weekDays.map(day => {
                      const schedule = userSchedules?.schedules?.[day.date];
                      
                      return (
                        <div 
                          key={day.date} 
                          className={`px-2 py-2 border-r border-slate-200 last:border-r-0 min-h-[60px] ${
                            day.isToday ? 'bg-teal-50/50' : ''
                          } ${day.isWeekend ? 'bg-slate-50' : ''}`}
                        >
                          {schedule ? (
                            <div 
                              onClick={() => handleOpenEdit(schedule)}
                              className={`p-2 rounded border cursor-pointer hover:shadow-sm transition-shadow ${getRoleColor(user.role)}`}
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-medium">{schedule.start_time}</span>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDelete(schedule.id);
                                  }}
                                  className="text-red-500 hover:text-red-700 opacity-50 hover:opacity-100"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </button>
                              </div>
                              <div className="text-xs text-slate-500">{schedule.end_time}</div>
                            </div>
                          ) : (
                            <button
                              onClick={() => {
                                setFormData({
                                  user_id: user.id,
                                  scheduled_date: day.date,
                                  start_time: '08:00',
                                  end_time: '16:00',
                                  max_duration_hours: 8,
                                  notes: ''
                                });
                                setShowCreateModal(true);
                              }}
                              className="w-full h-full min-h-[40px] border-2 border-dashed border-slate-200 rounded hover:border-teal-400 hover:bg-teal-50 transition-colors flex items-center justify-center"
                            >
                              <Plus className="w-4 h-4 text-slate-400" />
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })
            )}
          </div>
        )}
        
        {/* Légende */}
        <div className="flex items-center gap-4 text-sm text-slate-600">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-blue-100 border border-blue-200"></div>
            <span>Pharmacien</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-green-100 border border-green-200"></div>
            <span>Caissier</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-teal-100 border border-teal-200"></div>
            <span>Aujourd'hui</span>
          </div>
        </div>
      </div>
      
      {/* Modal Création */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-teal-700">
              <CalendarIcon className="w-5 h-5" />
              Nouvelle planification
            </DialogTitle>
            <DialogDescription>
              Planifier un shift pour un employé
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label>Employé *</Label>
              <Select 
                value={formData.user_id} 
                onValueChange={(v) => setFormData({ ...formData, user_id: v })}
              >
                <SelectTrigger className="mt-1" data-testid="select-user">
                  <SelectValue placeholder="Sélectionner un employé" />
                </SelectTrigger>
                <SelectContent>
                  {schedulableUsers.map(user => (
                    <SelectItem key={user.id} value={user.id}>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-1 rounded ${getRoleColor(user.role)}`}>
                          {user.employee_code}
                        </span>
                        {user.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>Date *</Label>
              <Input
                type="date"
                value={formData.scheduled_date}
                onChange={(e) => setFormData({ ...formData, scheduled_date: e.target.value })}
                className="mt-1"
                data-testid="input-date"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Heure de début</Label>
                <Input
                  type="time"
                  value={formData.start_time}
                  onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                  className="mt-1"
                  data-testid="input-start-time"
                />
              </div>
              <div>
                <Label>Heure de fin</Label>
                <Input
                  type="time"
                  value={formData.end_time}
                  onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                  className="mt-1"
                  data-testid="input-end-time"
                />
              </div>
            </div>
            
            <div>
              <Label>Durée maximale (heures)</Label>
              <Input
                type="number"
                min="1"
                max="12"
                value={formData.max_duration_hours}
                onChange={(e) => setFormData({ ...formData, max_duration_hours: parseFloat(e.target.value) || 8 })}
                className="mt-1"
                data-testid="input-max-duration"
              />
            </div>
            
            <div>
              <Label>Notes (optionnel)</Label>
              <Input
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Notes..."
                className="mt-1"
              />
            </div>
          </div>
          
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>
              Annuler
            </Button>
            <Button 
              onClick={handleCreate}
              disabled={createSchedule.isPending}
              className="bg-teal-600 hover:bg-teal-700"
              data-testid="confirm-create-btn"
            >
              {createSchedule.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Plus className="w-4 h-4 mr-2" />
              )}
              Créer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Modal Édition */}
      <Dialog open={showEditModal} onOpenChange={setShowEditModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-700">
              <Edit className="w-5 h-5" />
              Modifier la planification
            </DialogTitle>
          </DialogHeader>
          
          {selectedSchedule && (
            <div className="space-y-4">
              <div className="p-3 bg-slate-50 rounded-lg">
                <p className="font-medium text-slate-800">{selectedSchedule.user_name}</p>
                <p className="text-sm text-slate-500">{selectedSchedule.employee_code} • {selectedSchedule.scheduled_date}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Heure de début</Label>
                  <Input
                    type="time"
                    value={formData.start_time}
                    onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>Heure de fin</Label>
                  <Input
                    type="time"
                    value={formData.end_time}
                    onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                    className="mt-1"
                  />
                </div>
              </div>
              
              <div>
                <Label>Durée maximale (heures)</Label>
                <Input
                  type="number"
                  min="1"
                  max="12"
                  value={formData.max_duration_hours}
                  onChange={(e) => setFormData({ ...formData, max_duration_hours: parseFloat(e.target.value) || 8 })}
                  className="mt-1"
                />
              </div>
              
              <div>
                <Label>Notes</Label>
                <Input
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Notes..."
                  className="mt-1"
                />
              </div>
            </div>
          )}
          
          <DialogFooter className="mt-4 gap-2">
            <Button
              variant="destructive"
              onClick={() => handleDelete(selectedSchedule?.id)}
              disabled={deleteSchedule.isPending}
              className={confirmDelete ? "bg-red-700 hover:bg-red-800 text-white animate-pulse" : "bg-red-600 hover:bg-red-700 text-white"}
            >
              {deleteSchedule.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4 mr-2" />
              )}
              {confirmDelete ? "Confirmer la suppression ?" : "Supprimer"}
            </Button>
            {confirmDelete && (
              <Button variant="outline" onClick={() => setConfirmDelete(false)}>
                Non
              </Button>
            )}
            {!confirmDelete && (
              <Button variant="outline" onClick={() => setShowEditModal(false)}>
                Annuler
              </Button>
            )}
            {!confirmDelete && (
              <Button 
                onClick={handleUpdate}
                disabled={updateSchedule.isPending}
                className="bg-amber-600 hover:bg-amber-700"
              >
                {updateSchedule.isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Edit className="w-4 h-4 mr-2" />
                )}
                Enregistrer
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Modal Planification rapide (en masse) */}
      <Dialog open={showBulkModal} onOpenChange={setShowBulkModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-teal-700">
              <Copy className="w-5 h-5" />
              Planification rapide
            </DialogTitle>
            <DialogDescription>
              Sélectionnez plusieurs jours pour planifier un employé
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label>Employé *</Label>
              <Select 
                value={bulkData.user_id} 
                onValueChange={(v) => setBulkData({ ...bulkData, user_id: v })}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Sélectionner un employé" />
                </SelectTrigger>
                <SelectContent>
                  {schedulableUsers.map(user => (
                    <SelectItem key={user.id} value={user.id}>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-1 rounded ${getRoleColor(user.role)}`}>
                          {user.employee_code}
                        </span>
                        {user.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Heure de début</Label>
                <Input
                  type="time"
                  value={bulkData.start_time}
                  onChange={(e) => setBulkData({ ...bulkData, start_time: e.target.value })}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>Heure de fin</Label>
                <Input
                  type="time"
                  value={bulkData.end_time}
                  onChange={(e) => setBulkData({ ...bulkData, end_time: e.target.value })}
                  className="mt-1"
                />
              </div>
            </div>
            
            <div>
              <Label>Durée maximale (heures)</Label>
              <Input
                type="number"
                min="1"
                max="12"
                value={bulkData.max_duration_hours}
                onChange={(e) => setBulkData({ ...bulkData, max_duration_hours: parseFloat(e.target.value) || 8 })}
                className="mt-1 w-32"
              />
            </div>
            
            <div>
              <Label>Sélectionnez les jours ({bulkData.selectedDays.length} sélectionnés)</Label>
              <div className="mt-2 grid grid-cols-7 gap-1 p-3 bg-slate-50 rounded-lg border">
                {['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'].map(d => (
                  <div key={d} className="text-center text-xs font-medium text-slate-500 pb-1">{d}</div>
                ))}
                {monthDays.filter(d => d.isCurrentMonth).map((day, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => toggleBulkDay(day.date)}
                    className={`p-2 text-sm rounded transition-colors ${
                      bulkData.selectedDays.includes(day.date)
                        ? 'bg-teal-600 text-white'
                        : day.isToday
                          ? 'bg-teal-100 text-teal-800 hover:bg-teal-200'
                          : 'hover:bg-slate-200'
                    }`}
                  >
                    {day.day}
                  </button>
                ))}
              </div>
            </div>
          </div>
          
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowBulkModal(false)}>
              Annuler
            </Button>
            <Button 
              onClick={handleBulkCreate}
              disabled={createBulkSchedules.isPending || bulkData.selectedDays.length === 0}
              className="bg-teal-600 hover:bg-teal-700"
            >
              {createBulkSchedules.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Plus className="w-4 h-4 mr-2" />
              )}
              Créer {bulkData.selectedDays.length} planification(s)
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default ShiftSchedules;
