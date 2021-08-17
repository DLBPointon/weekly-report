import sys
from jira import JIRA
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta, date


def dotloader():
    load_dotenv()
    jira_user = os.getenv('JIRA_USER')
    jira_pass = os.getenv('JIRA_PASS')
    slack_add = os.getenv('SLACK_HOOK')
    return jira_user, jira_pass, slack_add


def authorise(user, password):
    jira = "https://grit-jira.sanger.ac.uk"
    auth_jira = JIRA(jira, basic_auth=(user, password))
    item_dict = {}
    item_list = []
    ticket_grit, ticket_rc, ticket_other, stat_today, stat_submitted = 0, 0, 0, 0, 0

    projects = auth_jira.search_issues(f'project IN ("GRIT","RC")', maxResults=10000)
    if len(projects) >= 1:
        for i in projects:
            issue = auth_jira.issue(f'{i}', expand='changelog')
            today = datetime.today().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S").split('T')
            for history in issue.changelog.histories:
                for item in history.items:
                    if item.toString in ['Open', 'Decontamination',
                                         'geval analysis', 'HiC Building',
                                         'gEVAL QC', 'curation',
                                         'Curation QC', 'Post Processing ++',
                                         'Submitted', 'In Submission']:

                        datetime_item = datetime \
                            .strptime(history.created,
                                      '%Y-%m-%dT%H:%M:%S.%f%z').strftime("%Y-%m-%dT%H:%M:%S").split('T')

                        time_diff = datetime.strptime(today[0],
                                                      '%Y-%m-%d') - datetime.strptime(datetime_item[0],
                                                                                      '%Y-%m-%d')
                        in_days = time_diff / timedelta(days=1)
                        end = 7 * int(sys.argv[1])
                        start = 7 * (int(sys.argv[1]) - 1)

                        if end >= int(in_days) >= start:
                            item_list.append('Today')
                            item_list.append(' @ '.join(today))
                            item_list.append(item.toString)
                            item_list.append(' @ '.join(datetime_item))
                            item_dict[f'{issue}'] = item_list
                        else:
                            pass

            item_list = []

        for i, ii in item_dict.items():
            if i.startswith('GRIT'):
                ticket_grit += 1
            elif i.startswith('RC'):
                ticket_rc += 1
            else:
                ticket_other += 1

            if ii[-2] == 'Submitted':
                stat_submitted += 1
            elif ii[-2] == 'Today':
                stat_today += 1

    return item_dict, ticket_other, ticket_rc, ticket_grit, stat_today, stat_submitted, auth_jira


def make_json(item_dict, ticket_other, ticket_rc, ticket_grit, stat_today, stat_submitted):
    list_of_items = ''
    for i, ii in item_dict.items():
        list_of_items += (f'  {i} | {ii[-2]} - {ii[-1]}' + '\n')

    message_package = '{"text":"\n' + \
        f'|----- Miss Minutes Report for {date.today()} START-----|\n' + \
        f'|========================================|\n' + \
        f'{list_of_items}\n' + \
        f'|========================================|\n' + \
        f' \tGRIT = {ticket_grit} || RC = {ticket_rc} || OTHER = {ticket_other}\n' + \
        f'|============ THIS WEEK \\/ ==============|\n' + \
        f' \tSubmitted = {stat_submitted} || Opened = {stat_today}\n' + \
        f'|========================================|\n'

    return message_package


def new_tickets(auth_jira, message):
    projects = auth_jira.search_issues(f'project IN ("GRIT","RC") AND status = Open',
                                       maxResults=10000)
    new_list = ''
    counter = 0
    for i in projects:
        new_list += str(f'{i}, ')
        counter += 1
        if counter == 8:
            counter = 0
            new_list += ' \n '
        else:
            pass

    message += f'|===========> OPEN TICKETS <=============|\n' + \
               f' {new_list}\n'

    return message


def fin_tickets(auth_jira, message):
    projects = auth_jira.search_issues(f'project IN ("GRIT","RC") AND status = Submitted',
                                       maxResults=10000)
    print('________________')
    new_list = ''
    counter = 0
    for i in projects:
        new_list += str(f'{i}, ')
        counter += 1
        if counter == 8:
            counter = 0
            new_list += ' \n '
        else:
            pass

    message += f'|===========> FIN TICKETS <=============|\n' + \
               f' {new_list}\n' + \
               f'|----- Miss Minutes Report for {date.today()} END -----|' + \
               '"}'

    return message


def post_it(json, hook):
    os.popen(f"curl -X POST -H 'Content-type: application/json' --data '{json}' {hook}").read()


def main():
    user, passw, slack = dotloader()
    item_dict, ticket_other, ticket_rc, ticket_grit, stat_today, stat_submitted, auth_jira = authorise(user, passw)
    message = make_json(item_dict, ticket_other, ticket_rc, ticket_grit, stat_today, stat_submitted)
    message_new = new_tickets(auth_jira, message)
    final_message = fin_tickets(auth_jira, message_new)
    print(final_message)
    post_it(final_message, slack)


if __name__ == '__main__':
    main()
