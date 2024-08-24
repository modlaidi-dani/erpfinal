class TaxesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "clientInfo/taxes_page.html"
    login_url = 'home' 
    raise_exception = True  # Set to True to raise a PermissionDenied exception
    def test_func(self):
        # Define the custom test function
        myuser=CustomUser.objects.get(username=self.request.user.username)
        print('hello',self.request.session.get('permissions', []))
        return('clientInfo.can_see_tax_douan' in self.request.session.get('permissions', []) or 'clientInfo.can_see_tax_tva' in self.request.session.get('permissions', []))

    def handle_no_permission(self):
         # Redirect users without permission to the "inventory" page
        return HttpResponseRedirect(reverse_lazy('inventory'))