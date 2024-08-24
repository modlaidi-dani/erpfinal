from django.urls import path

from . import views

urlpatterns = [
    path('', views.loginInto, name='home'),  
    path('ListeUser', views.ListeUsers.as_view(), name='users'),  
    path('userHome/', views.UserhomePage.as_view(), name='user-page'), 
    path('Edit-user/<str:username_user>', views.UpdateUser.as_view(), name='update-user'),  
    path('supprimerUtilisateur/', views.DeleteUser, name='delete-user'),  
    path('supprimerGroup/', views.DeleteGroupe, name='delete-grp'),  
    path('Profile', views.Profile.as_view(), name='profile'),  
    path('Notifications', views.NotificationsView.as_view(), name='notifications'),  
    path('new-group', views.ListePermissions.as_view(), name='new-group'),  
    path('Groupes', views.ListeGroupes.as_view(), name='groups'),  
    path('Edit-group/<int:group_id>', views.GroupeUpdate.as_view(), name='update-group'),  
    path('adminPage', views.adminMag,name="magasins"),
    path('CoursesPage', views.ChauffeurPageLogin.as_view(), name="chauffeur-page"),
    path('signup', views.signup, name='signup'),
    path('logout', views.logout_view, name='logout'),
    path('noPermission', views.RedirectPermissionNone.as_view(), name='noaccess'),
    path('UserPermissions', views.user_permission.as_view(), name='user-permissions'),
    path('EditUserPermissions/<str:username_user>', views.Edituser_permission.as_view(), name='edit-user-permissions'),
]